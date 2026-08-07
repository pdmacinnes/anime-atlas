# Mobile Support Spec

## Requirements & Goals

Anime Atlas (`docs/index.html`) currently only works well on desktop:
the sidebar is a hardcoded 260px-wide fixed panel, the canvas only
listens for mouse events (`mousedown`/`mousemove`/`mouseup`/`wheel`),
and the count badge and detail panel are positioned/sized assuming
desktop screen widths. On a phone the sidebar eats most of the
viewport, there's no way to pan/zoom/select with touch, and pinch
gestures would trigger the browser's native page zoom instead.

Goal: make the existing single-page app fully usable on phone-sized
touchscreens (~360-430px wide) without changing desktop behavior or
introducing a build step -- this stays a single static HTML file.

## Inputs, Outputs & Behavior

**Touch interaction on canvas (new):**
- Single-finger drag pans the view (mirrors mouse drag).
- Two-finger pinch zooms around the pinch midpoint (mirrors wheel zoom).
- A tap (touch start/end with negligible movement, same threshold as
  the existing click logic) selects the nearest point and opens the
  detail panel (mirrors mouse click).
- `touch-action: none` on the canvas so the browser doesn't intercept
  gestures for native scroll/zoom.

**Sidebar (responsive layout):**
- Below a breakpoint (~700px viewport width), the sidebar becomes a
  slide-in drawer instead of a permanently docked 260px panel:
  - Collapsed by default, off-canvas (translated off the left edge).
  - A hamburger-style toggle button (fixed top-left) opens/closes it.
  - When open, it overlays the canvas (canvas remains interactive
    underneath is not required -- standard drawer-over-content pattern)
    and can be closed via the toggle button or by tapping outside it.
  - Above the breakpoint, behavior is unchanged: always-visible docked
    sidebar, no toggle button shown.

**Count badge:**
- Currently hardcoded `left: 274px` (assumes the docked sidebar's
  width). On mobile it must not be pinned to a spot that's either
  hidden under the collapsed drawer's toggle button or irrelevant once
  the sidebar is off-canvas. Below the breakpoint it repositions to a
  small fixed offset from the left edge (e.g. `14px`, matching its
  existing bottom offset), since the sidebar is no longer docked.

**Detail panel:**
- Currently fixed `width: 260px` anchored bottom-right. Below the
  breakpoint, width becomes responsive (`calc(100vw - 32px)` or
  similar) so it never overflows a narrow viewport, staying anchored
  bottom with symmetric side margins.

**Non-goals:**
- No changes to desktop mouse/wheel behavior.
- No changes to data, filters, color logic, or the pipeline.
- No build tooling introduced -- stays inline CSS/JS in the one file.

## Edge Cases & Error Handling

- Pinch zoom must not also fire a pan (two-finger midpoint tracking
  replaces single-finger delta tracking while a second touch is down).
- Lifting one finger during a pinch (going from 2 touches to 1) must
  not cause a jump -- reset the drag anchor when the touch count
  changes rather than assuming continuity.
- Tap-to-select must use the same movement threshold as the existing
  mouse click (`DRAG_THRESHOLD_PX`) so a slightly-jittery tap doesn't
  get misread as a pan.
- Opening the drawer must not break existing sidebar scrolling
  (genre list `overflow-y: auto`) or existing desktop styles.
- Rotating a phone (viewport crossing the breakpoint) shouldn't leave
  the drawer in a broken state -- closing state driven by a CSS class
  toggled by JS, checked against the media query via CSS alone where
  possible.
- `resizeCanvas` already runs on `window resize` -- verify it still
  fires correctly on mobile orientation change (it does, `resize` is
  the right event).

## Acceptance Criteria

- [ ] On a phone-width viewport, the canvas is usable full-screen by
      default (sidebar collapsed, not eating the viewport).
- [ ] A visible toggle control opens/closes the sidebar drawer on
      mobile; sidebar content and behavior (filters, search, etc.)
      is unchanged once open.
- [ ] Single-finger drag pans the canvas on touch devices.
- [ ] Two-finger pinch zooms the canvas on touch devices, centered on
      the pinch point.
- [ ] Tapping a point selects it and opens the detail panel, same as
      a desktop click.
- [ ] The detail panel never overflows the viewport width on a phone.
- [ ] The count badge is never hidden or overlapping the toggle button
      on mobile.
- [ ] Desktop (viewport above breakpoint) behavior/appearance is
      pixel-identical to before this change.
- [ ] No build step added; still a single static `docs/index.html`.
