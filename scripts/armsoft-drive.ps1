param([string]$Do = "shot", [int]$X = 0, [int]$Y = 0, [string]$Text = "", [string]$Out = "shot.png", [int]$Wait = 800)
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
Add-Type @"
using System; using System.Text; using System.Runtime.InteropServices; using System.Collections.Generic;
public class W {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, UIntPtr e);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint a, uint b, bool f);
  [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc p, IntPtr l);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  public struct RECT { public int L, T, R, B; }
  public static List<string> Wins(uint pid) {
    var l = new List<string>();
    EnumWindows((h, p) => { uint q; GetWindowThreadProcessId(h, out q);
      if (q == pid && IsWindowVisible(h)) { var s = new StringBuilder(300); GetWindowText(h, s, 300); RECT r; GetWindowRect(h, out r);
        l.Add(h.ToInt64() + " | " + s + " | " + r.L + "," + r.T + "," + r.R + "," + r.B); }
      return true; }, IntPtr.Zero);
    return l; }
  public static void Front(IntPtr h) {
    uint x; uint ft = GetWindowThreadProcessId(GetForegroundWindow(), out x); uint me = GetCurrentThreadId();
    AttachThreadInput(me, ft, true); if (IsIconic(h)) ShowWindow(h, 9); SetForegroundWindow(h); AttachThreadInput(me, ft, false); }
}
"@
[W]::SetProcessDPIAware() | Out-Null
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$p = Get-Process "AS Trade" | Select-Object -First 1
function Shot {
  Start-Sleep -Milliseconds $Wait
  $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
  $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
  $bmp.Save((Join-Path $dir $Out)); $g.Dispose(); $bmp.Dispose()
}
function Click([int]$n) {
  [W]::SetCursorPos($X, $Y) | Out-Null; Start-Sleep -Milliseconds 150
  for ($i = 0; $i -lt $n; $i++) { [W]::mouse_event(2, 0, 0, 0, [UIntPtr]::Zero); [W]::mouse_event(4, 0, 0, 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds 90 }
}
switch ($Do) {
  "wins"  { [W]::Wins([uint32]$p.Id) }
  "front" { if ($X) { [W]::Front([IntPtr]$X) } else { [W]::Front($p.MainWindowHandle) }; Shot }
  "shot"  { Shot }
  "click" { Click 1; Shot }
  "dbl"   { Click 2; Shot }
  "drag"  { $t = $Text.Split(','); [W]::SetCursorPos($X, $Y) | Out-Null; Start-Sleep -Milliseconds 200; [W]::mouse_event(2, 0, 0, 0, [UIntPtr]::Zero)
            $tx = [int]$t[0]; $ty = [int]$t[1]; for ($i = 1; $i -le 10; $i++) { [W]::SetCursorPos($X + ($tx - $X) * $i / 10, $Y + ($ty - $Y) * $i / 10) | Out-Null; Start-Sleep -Milliseconds 40 }
            [W]::mouse_event(4, 0, 0, 0, [UIntPtr]::Zero); Shot }
  "paste" { $t = [System.IO.File]::ReadAllText((Join-Path $dir $Text), [System.Text.Encoding]::UTF8).Trim(); [System.Windows.Forms.Clipboard]::SetText($t); Start-Sleep -Milliseconds 200; [System.Windows.Forms.SendKeys]::SendWait("^v"); Shot }
  "keys"  { [System.Windows.Forms.SendKeys]::SendWait($Text); Shot }
}
