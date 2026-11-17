"""Admin content: FAQ, blog and CMS pages. Shapes come from siruk-web/backend/app:
Http/Requests/Admin/Blog/PostStoreRequest.php + PostUpdateRequest.php (a post needs post_category_id, title, slug;
`image` is a media id), Http/Resources/Admin/Blog/SinglePostResource.php (the record), PostResource.php (the list row),
Http/Resources/Admin/Faq/FaqResource.php, Http/Controllers/Admin/Common/PageController.php (`{data: ...}`, PUT fills the
keys sent) and Http/Resources/Admin/Page/FaqsPageResource.php."""
import json

import pytest

from siruk import cli
from siruk.admin import content, policy
from siruk.payload import PayloadError

NOUNS = ("faq-categories", "faqs", "post-categories", "authors", "vets", "posts")


def run(argv):
    with pytest.raises(SystemExit) as e:
        cli.main(["-q", *argv])
    return e.value.code


def writes(fc):
    return [c for c in fc.calls if c[0] != "GET"]


def plan(capsys, argv):
    capsys.readouterr()
    assert run([*argv, "--json"]) == 0
    return json.loads(capsys.readouterr().out)


# SinglePostResource::toArray; its content_blocks are PostBlockResource::toArray (id, type, text)
def post(i=7, **kw):
    return {"id": i, "post_category_id": 2, "author_ids": [1], "vet_reviews": [], "title": "Puppy food",
            "slug": "puppy-food", "featured_description": "short", "content": "<p>x</p>", "image": 31,
            "desktop_image": None, "mobile_image": None,
            "content_blocks": [{"id": 11, "type": "text", "text": "Feed twice a day."}], "is_published": False,
            "is_featured": False, "published_at": None, "createdAt": "2026-01-02", "updatedAt": "2026-01-02", **kw}


# PostStoreRequest::rules
CREATE = {"post_category_id": 2, "title": "Puppy food", "slug": "puppy-food", "image": 31,
          "content_blocks": [{"type": "text", "text": "Feed twice a day."}]}
# the whole record `show --json` gives back, with the block ids PostController::syncContentBlocks keeps blocks by
HY = {**CREATE, "title": "Շան կեր", "author_ids": [1],
      "content_blocks": [{"id": 11, "type": "text", "text": "Կերակրել օրական երկու անգամ։"}]}
# FaqsPageResource::toArray
FAQS_PAGE = {"title": "Questions", "subtitle": "Answers", "createdAt": None, "updatedAt": None}


def test_every_noun_and_verb_has_its_manifest_fields(capsys):
    assert run(["commands", "--json"]) == 0
    by = {r["name"]: r for r in json.loads(capsys.readouterr().out)}
    tiers = {"list": "read", "show": "read", "create": "draft", "update": "draft", "delete": "irreversible"}
    for noun in NOUNS:
        for verb, tier in tiers.items():
            r = by[f"admin {noun} {verb}"]
            assert r["tier"] == tier and r["backend"] == "admin" and r["api"] and r["help"] and r["example"] and r["roles"]
    assert by["admin pages show"]["tier"] == "read" and by["admin pages set"]["tier"] == "draft"
    assert "admin pages delete" not in by


def test_every_resource_names_its_required_keys_and_source():
    assert [r.required for r in content.NOUNS.values()] == [
        ("name",), ("category_id", "question", "answer"), ("name", "slug"), ("name",), ("name",),
        ("post_category_id", "title", "slug")]
    assert all(r.source and r.translatable for r in content.NOUNS.values())
    for res in content.NOUNS.values():
        assert policy.allowed("POST", res.path) is None and policy.allowed("DELETE", res.path + "/5") is None
    assert policy.allowed("PUT", "/pages/about-us") is None


def test_post_create_in_en_and_update_in_hy(admin_fake, capsys):
    admin_fake.on("GET", "/posts", {"data": []}).on("POST", "/posts", {"data": post()})
    argv = ["admin", "posts", "create", json.dumps(CREATE), "--lang", "en"]
    p = plan(capsys, argv)
    assert p["tier"] == "draft" and writes(admin_fake) == []
    assert run([*argv, "--apply", p["code"]]) == 0
    assert writes(admin_fake) == [("POST", "/posts", CREATE)] and admin_fake.langs[-1] == "en"

    admin_fake.on("GET", "/posts/7", {"data": post()}).on("PUT", "/posts/7", {"data": post()})
    hy = HY
    argv = ["admin", "posts", "update", "7", json.dumps(hy, ensure_ascii=False), "--lang", "hy"]
    p = plan(capsys, argv)
    assert 'title: "Puppy food" → "Շան կեր"' in p["summary"] and "(Content-Language hy)" in p["summary"]
    assert run([*argv, "--apply", p["code"]]) == 0
    assert writes(admin_fake)[-1] == ("PUT", "/posts/7", hy) and admin_fake.langs[-1] == "hy"
    assert [m for m, *_ in writes(admin_fake)] == ["POST", "PUT"]


def test_the_same_body_in_another_language_gets_another_code(admin_fake, capsys):
    admin_fake.on("GET", "/posts/7", {"data": post()})
    argv = ["admin", "posts", "update", "7", json.dumps({**HY, "title": "Շուն"}, ensure_ascii=False)]
    codes = {lang: plan(capsys, [*argv, "--lang", lang])["code"] for lang in ("ru", "hy")}
    assert codes["ru"] != codes["hy"]
    assert run([*argv, "--lang", "hy", "--apply", codes["ru"]]) == 1 and writes(admin_fake) == []


def test_create_is_en_only_and_refuses_a_missing_required_key(admin_fake):
    assert run(["admin", "posts", "create", json.dumps(CREATE), "--lang", "ru"]) == 1
    for body in ({"title": "x", "slug": "x"}, {"post_category_id": 2, "title": "", "slug": "x"}, [1]):
        assert run(["admin", "posts", "create", json.dumps(body)]) == 1
    assert admin_fake.calls == []


@pytest.mark.parametrize("body", [
    {"post_category_id": 2, "title": "t", "slug": "t", "image": "https://x.test/a.jpg"},
    {"post_category_id": 2, "title": "t", "slug": "t", "content_blocks": [{"type": "image", "image": "a.jpg"}]},
])
def test_an_image_url_is_refused_before_any_call(admin_fake, body):
    assert run(["admin", "posts", "create", json.dumps(body)]) == 1 and admin_fake.calls == []


def test_media_ids_pass_the_image_check():
    content.check_images({"image": 31, "desktop_image": "32", "banner_image": None,
                          "content_blocks": [{"type": "image", "image": [4, 5]}, {"type": "text", "text": "x"}]})
    with pytest.raises(PayloadError):
        content.check_images({"profile_image": "https://x.test/a.jpg"})


@pytest.mark.parametrize("noun, path, rec, label", [
    ("posts", "/posts/7", post(), "Puppy food"),
    # FaqResource::toArray
    ("faqs", "/faqs/3", {"id": 3, "category_id": 1, "category_name": "Orders", "question": "How long?",
                         "answer": "Two days.", "createdAt": None, "updatedAt": None}, "How long?"),
    # AuthorResource::toArray
    ("authors", "/authors/4", {"id": 4, "name": "Anna", "profile_image": 9, "createdAt": None, "updatedAt": None},
     "Anna"),
    # VetResource::toArray
    ("vets", "/vets/6", {"id": 6, "name": "Dr Ara", "profile_image": None, "social_links": [], "createdAt": None,
                         "updatedAt": None}, "Dr Ara"),
    # FaqCategoryResource::toArray
    ("faq-categories", "/faq-categories/1", {"id": 1, "name": "Orders", "createdAt": None, "updatedAt": None}, "Orders"),
    # PostCategoryResource::toArray
    ("post-categories", "/post-categories/2", {"id": 2, "name": "Food", "slug": "food", "parent_id": None}, "Food"),
])
def test_delete_is_irreversible_and_shows_the_record(admin_fake, capsys, noun, path, rec, label):
    admin_fake.on("GET", path, {"data": rec}).on("DELETE", path, None)
    rid = path.rsplit("/", 1)[1]
    p = plan(capsys, ["admin", noun, "delete", rid])
    assert p["tier"] == "irreversible" and p["requests"][0]["method"] == "DELETE" and p["requests"][0]["path"] == path
    assert f"({label})" in p["summary"] and writes(admin_fake) == []
    admin_fake.on("GET", path, {"data": {**rec, "updatedAt": "changed meanwhile"}})
    assert run(["admin", noun, "delete", rid, "--apply", p["code"]]) == 1 and writes(admin_fake) == []
    admin_fake.on("GET", path, {"data": rec})
    assert run(["admin", noun, "delete", rid, "--apply", p["code"]]) == 0
    assert writes(admin_fake) == [("DELETE", path, None)]


def test_list_and_show_post(admin_fake, capsys):
    # PostResource::toArray
    row = {"id": 7, "category_name": "Food", "author_name": "Anna", "vet_name": "", "title": "Puppy food",
           "slug": "puppy-food"}
    admin_fake.on("GET", "/posts", {"data": [row]}).on("GET", "/posts/7", {"data": post()})
    assert run(["admin", "posts", "list", "--search", "puppy", "--lang", "hy"]) == 0
    assert "Puppy food" in capsys.readouterr().out
    assert admin_fake.calls[0][:2] == ("GET", "/posts?search=puppy") and admin_fake.langs[0] == "hy"
    assert run(["admin", "posts", "show", "7", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {"data": post()}


def test_faq_create_needs_its_three_keys(admin_fake, capsys):
    assert run(["admin", "faqs", "create", '{"question": "How long?"}']) == 1 and admin_fake.calls == []
    body = {"category_id": 1, "question": "How long?", "answer": "Two days."}
    admin_fake.on("GET", "/faqs", {"data": []}).on("POST", "/faqs", {"data": {"id": 3}})
    p = plan(capsys, ["admin", "faqs", "create", json.dumps(body)])
    assert run(["admin", "faqs", "create", json.dumps(body), "--apply", p["code"]]) == 0
    assert writes(admin_fake) == [("POST", "/faqs", body)]


def test_pages_show_and_set_in_a_language(admin_fake, capsys):
    admin_fake.on("GET", "/pages/faqs", {"data": FAQS_PAGE}).on("PUT", "/pages/faqs", {"data": FAQS_PAGE})
    assert run(["admin", "pages", "show", "faqs", "--lang", "ru", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {"data": FAQS_PAGE} and admin_fake.langs[-1] == "ru"
    body = {"title": "Вопросы"}
    argv = ["admin", "pages", "set", "faqs", json.dumps(body, ensure_ascii=False), "--lang", "ru"]
    p = plan(capsys, argv)
    assert 'title: "Questions" → "Вопросы"' in p["summary"] and p["tier"] == "draft"
    assert run([*argv, "--apply", p["code"]]) == 0
    assert writes(admin_fake) == [("PUT", "/pages/faqs", body)] and admin_fake.langs[-1] == "ru"
    assert plan(capsys, [*argv[:-1], "hy"])["code"] != p["code"]


def test_an_unknown_page_is_refused_before_any_call(admin_fake):
    assert run(["admin", "pages", "show", "contact"]) == 1
    assert run(["admin", "pages", "set", "../posts", "{}"]) == 1
    assert admin_fake.calls == []


@pytest.mark.parametrize("path", ["/global-data", "/reposition", "/replicate-record"])
def test_the_unbuilt_routes_stay_refused(path):
    assert policy.allowed("POST", path)


@pytest.mark.parametrize("body, key", [
    ({k: v for k, v in HY.items() if k != "content_blocks"}, "content_blocks"),
    ({k: v for k, v in HY.items() if k != "author_ids"}, "author_ids"),
    ({**HY, "content_blocks": [{"id": 12, "type": "text", "text": "other"}]}, "block id 11"),
    ({**HY, "content_blocks": [{"id": None, "type": "text", "text": "x"}]}, "block id 11"),
])
def test_a_post_update_that_would_wipe_what_it_leaves_out_is_refused(admin_fake, capsys, body, key):
    admin_fake.on("GET", "/posts/7", {"data": post()})
    assert run(["admin", "posts", "update", "7", json.dumps(body, ensure_ascii=False), "--lang", "hy"]) == 1
    assert key in capsys.readouterr().err and writes(admin_fake) == []


def test_a_post_update_without_vet_reviews_is_refused_when_the_post_has_them(admin_fake, capsys):
    cur = post(vet_reviews=[{"vet_id": 6, "review_text": "ok"}])
    admin_fake.on("GET", "/posts/7", {"data": cur})
    body = {k: v for k, v in HY.items() if k != "vet_reviews"}
    assert run(["admin", "posts", "update", "7", json.dumps(body, ensure_ascii=False)]) == 1
    assert "vet_reviews" in capsys.readouterr().err and writes(admin_fake) == []


def test_clearing_on_purpose_and_the_show_wrapper_pass(admin_fake, capsys):
    admin_fake.on("GET", "/posts/7", {"data": post()}).on("PUT", "/posts/7", {"data": post()})
    clear = {**HY, "content_blocks": [], "author_ids": []}
    assert plan(capsys, ["admin", "posts", "update", "7", json.dumps(clear)])["requests"][0]["body"] == clear
    more = {**HY, "content_blocks": [*HY["content_blocks"], {"type": "image", "image": [31]}]}
    assert plan(capsys, ["admin", "posts", "update", "7", json.dumps(more)])["requests"][0]["body"] == more
    wrapped = plan(capsys, ["admin", "posts", "update", "7", json.dumps({"data": post()})])
    assert wrapped["requests"][0]["body"] == post()


@pytest.mark.parametrize("body", [
    {"hero_image": "https://x.test/a.jpg"},
    {"features": [{"title": "t", "icon": "bolt.svg"}]},
    {"file_main_en": "banner.png"},
    {"meta": {"title": "t"}, "meta_image": "https://x.test/m.jpg"},
])
def test_a_page_image_that_is_not_a_media_id_is_refused(admin_fake, body):
    assert run(["admin", "pages", "set", "about-us", json.dumps(body)]) == 1 and admin_fake.calls == []
    content.check_images({"hero_image": 4, "follow_images": [5, 6], "file_main_en": "7",
                          "features": [{"title": "t", "icon": 8}]})


def test_post_meta_image_is_checked(admin_fake):
    body = {**HY, "meta_image": "https://x.test/m.jpg"}
    assert run(["admin", "posts", "update", "7", json.dumps(body, ensure_ascii=False)]) == 1 and admin_fake.calls == []


def test_a_page_dry_run_names_the_seo_and_group_side_effects(admin_fake, capsys):
    admin_fake.on("GET", "/pages/about-us", {"data": {"title": "About", "features": []}})
    p = plan(capsys, ["admin", "pages", "set", "about-us",
                      json.dumps({"meta": {"title": "t"}, "features": [{"id": 1, "title": "x"}]})])
    assert "meta without meta_image clears the SEO image" in p["summary"]
    assert "features replaces the whole group" in p["summary"]
    assert "features replaces the whole group" in plan(
        capsys, ["admin", "pages", "set", "about-us", json.dumps({"features": []})])["summary"]
    p = plan(capsys, ["admin", "pages", "set", "about-us", json.dumps({"title": "x", "follow_images": [5, 6]})])
    assert "NOTE" not in p["summary"]


@pytest.mark.parametrize("noun, path, note", [
    ("faq-categories", "/faq-categories/1", "also deletes every FAQ in that category"),
    ("post-categories", "/post-categories/2", "its posts are left without a category"),
])
def test_a_category_delete_says_what_else_goes(admin_fake, capsys, noun, path, note):
    admin_fake.on("GET", path, {"data": {"id": 1, "name": "Orders"}})
    assert note in plan(capsys, ["admin", noun, "delete", path.rsplit("/", 1)[1]])["summary"]


def test_the_create_manifest_lists_its_search_and_posts_update_shows_the_round_trip(capsys):
    assert run(["commands", "--json"]) == 0
    by = {r["name"]: r for r in json.loads(capsys.readouterr().out)}
    assert by["admin posts create"]["api"] == ["GET /posts?search=", "POST /posts"]
    assert "posts show 7 --json" in by["admin posts update"]["example"]
    assert content.PAGES.required == ()
