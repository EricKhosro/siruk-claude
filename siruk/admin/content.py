"""The content resources behind `siruk admin faqs|posts|...|pages`: what each route family needs, read from the
Laravel controllers and FormRequests named in `source`.

Rules: a create names every key the API requires (a post: category, title, slug); an image is a media id from
`siruk media upload`, never a URL; a page is one of the nine the panel edits.
"""
from siruk.admin.resource import Resource
from siruk.payload import PayloadError

_BLOG = "app/Http/Controllers/Admin/Blog/"
_FAQ = "app/Http/Controllers/Admin/Faq/"

FAQ_CATEGORIES = Resource("FAQ category", "/faq-categories", required=("name",), translatable=True,
                          source=_FAQ + "FaqCategoryController.php; database/migrations/2025_12_07_000016_create_faqs_table.php")
FAQS = Resource("FAQ", "/faqs", required=("category_id", "question", "answer"), translatable=True, label="question",
                source=_FAQ + "FaqController.php; database/migrations/2025_12_07_000016_create_faqs_table.php")
POST_CATEGORIES = Resource("post category", "/post-categories", required=("name", "slug"), translatable=True,
                           source="app/Http/Requests/Admin/Blog/PostCategoryStoreRequest.php")
AUTHORS = Resource("author", "/authors", required=("name",), translatable=True, source=_BLOG + "AuthorController.php")
VETS = Resource("vet", "/vets", required=("name",), translatable=True, source=_BLOG + "VetController.php")
POSTS = Resource("post", "/posts", required=("post_category_id", "title", "slug"), translatable=True, label="title",
                 source="app/Http/Requests/Admin/Blog/PostStoreRequest.php")
PAGES = Resource("page", "/pages", required=(), translatable=True, deletable=False, label="title",
                 source="app/Http/Controllers/Admin/Common/PageController.php")

NOUNS = {"faq-categories": FAQ_CATEGORIES, "faqs": FAQS, "post-categories": POST_CATEGORIES, "authors": AUTHORS,
         "vets": VETS, "posts": POSTS}
PAGE_SLUGS = ("home", "about-us", "ser-club", "use-app", "privacy-policy", "terms-and-conditions", "faqs", "blog",
              "shop")
DELETE_NOTES = {"/faq-categories": "also deletes every FAQ in that category",
                "/post-categories": "its posts are left without a category"}
# what a post update wipes when the body leaves it out (PostController::update, syncContentBlocks, syncAuthorsAndVets)
KEPT_ON_UPDATE = ("content_blocks", "author_ids", "vet_reviews")


def page_slug(slug):
    if slug not in PAGE_SLUGS:
        raise PayloadError(f"unknown page {slug!r}: one of {', '.join(PAGE_SLUGS)}")
    return slug


def _is_media_id(v):
    if isinstance(v, list):
        return all(_is_media_id(i) for i in v)
    return v in (None, "") or (isinstance(v, int) and not isinstance(v, bool)) or (isinstance(v, str) and v.isdigit())


def _media_key(k):
    return "image" in k or k.startswith("file_") or k == "icon"


def check_images(body, where=""):
    """Refuse an image or icon given as a URL or a name, at any depth: the API takes a media id (or a list of them)."""
    if isinstance(body, list):
        for i, v in enumerate(body):
            check_images(v, f"{where}[{i}]")
    elif isinstance(body, dict):
        for k, v in body.items():
            here = f"{where}.{k}" if where else str(k)
            if _media_key(str(k)):
                if not _is_media_id(v):
                    raise PayloadError(f"{here} must be a media id from `siruk media upload`, not {str(v)[:60]!r}")
            else:
                check_images(v, here)


def unwrap(body):
    """`show --json` answers {"data": record}: the record is what an update sends back."""
    return body["data"] if isinstance(body, dict) and set(body) == {"data"} and isinstance(body["data"], dict) else body


def check_post_update(id, body, cur):
    """Refuse an update that would wipe blocks, authors or vet reviews the body leaves out; a block without an id is a new one."""
    redo = f"`siruk admin posts show {id} --json`, edit it, send the whole record (send [] to clear on purpose)"
    for key in KEPT_ON_UPDATE:
        if key not in body and cur.get(key):
            raise PayloadError(f"the body lacks {key}, which the post has: the update would clear it; {redo}")
    sent = {b.get("id") for b in body.get("content_blocks") or [] if isinstance(b, dict)}
    # an empty list is the deliberate clear the message offers
    gone = [b["id"] for b in cur.get("content_blocks") or [] if sent and b.get("id") not in sent]
    if gone:
        raise PayloadError(f"content block id {', '.join(map(str, gone))} is not in the body, so the update deletes it; {redo}")


def page_notes(body):
    """What a page write does beyond the keys it names, for the dry run."""
    notes = []
    if "meta" in body and "meta_image" not in body:
        notes.append("meta without meta_image clears the SEO image")
    notes += [f"{k} replaces the whole group (components not sent are deleted; send each one's id to keep it)"
              for k, v in body.items() if isinstance(v, list) and not _media_key(str(k))]
    return notes
