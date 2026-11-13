---
name: social-demo-video-planning
description: "Use when planning or storyboarding launch videos for X."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [x, twitter, launch-video, storyboard, attention, demo]
    related_skills: [fframes-video-via-fframestudio, xurl, agent-reach, making-of-case-study, rendered-ui-qualification]
---

# Planning launch/demo videos for X

The owner (@_kvnloo) wants short native X videos that make his product work visible, especially Hermes × Tern, desktop and CLI UX. The deliverable is a storyboard he can review in fframestudio and a capture plan, not a strategy essay.

## Procedure
1. **Read his own history first, with numbers.** Run `twitter user-posts _kvnloo -n 200 --json` (agent-reach twitter-cli; read-only). Split his own posts from retweets. Compare views by format (text, photo, video) and list the Hermes posts with views, likes and video length (`ffprobe` the `video.twimg.com` URL).
   - Treat the videos he **retweeted** as his taste reference library. Sort them by views and hand that list to researchers as verified case studies.
   - `twitter tweet <id> --json` gives a post plus its replies, which shows maintainer reactions.
   - The browser-use browser gets 403 from x.com, and xurl needs the owner's paid dev app; use twitter-cli.
2. **Research in parallel, synthesize in the parent.** Use 3 Sol plus 2 free-lane workers when burn-pace allows. Slices:
   - viral demo case studies, with format archetypes and why each worked;
   - X ranking and distribution mechanics, from the algorithm source;
   - production craft and pipeline;
   - terminal/TUI launch videos;
   - the project ecosystem's own accounts.

   Give each worker his baseline file. Write reports into the project's kitchen run dir, then a `SYNTHESIS.md` (rules, slate, gaps).
3. **Inventory what already exists before proposing new work.** Check `~/.config/fframestudio/sources.json`, the storyboards (e.g. `hermes-wt/demo-capture-out/storyboards/storyboards.md`) and every rendered cut. Match posted videos to local files by duration. Build a frame sheet (0.3 s, 1.5 s, 3 s, then 30/50/70/95%) and judge each cut's first 3 seconds.
4. **Pick features by user benefit (owner rule).** Lead with UX engineering features that make the product nicer and faster to use: thinking orbs / continuous voice, subagent visibility, the context window mini popup and detailed view, rewind/fork, drafts that are never lost, artifacts beside chat. Do not lead with architecture or protocol claims ("typed nodes instead of cells"). A strong hook pointed at an engineer-only claim is the wrong video. Frame the series around turning ideas into results faster.
5. **Storyboard in fframes** (see `fframes-video-via-fframestudio`): one panel per beat, real product screenshots as plates, and the on-screen caption, shot direction and honest status label (merged / open PR / branch) on each panel. Template crate: `workspace/zer0/products/hermes-tern-ux-storyboard/` (`BRIEF.md`, `fframes/src/lib.rs`). Hatch panels whose plate is a stand-in for footage not yet recorded.
6. **Let him review on his phone.** Import into fframestudio and open the tailnet URL on the S25 in Chrome (recipe in the fframes skill). Don't send loose PNGs to the gallery when he asked for fframestudio.
7. **Capture real interaction** in a studio output (`references/studio-capture.md`). Animated stills are not a demo.

## Attention rules (apply to every cut)
- Frame 0 is the thumbnail and the autoplay start. Open on the payoff state with one line of large text, never on a logo, title card or empty pane.
- One benefit per video, phrased as the viewer's gain.
- Captions carry every claim with the sound off; big overlay type states the claim and the UI proves it.
- The window fills at least 70% of the frame. Push in on the one line that matters; terminal text at feed size needs about 40 px effective type.
- Use suspense structures (timer, red→green, race, "will it…") because dwell is ranked. Replace lockup endings with a cut back to frame 0 so the clip loops.
- Keep honest proof devices ("REAL SPEED · NOT EDITED") when true.
- Posts lead with the benefit plus a specific question. A specific design question beat a bare title several times over in his own history. State status in the post and put credits and the link in a reply.
- Private previews go to the relevant maintainer for feedback, not for reposts.

## Pitfalls
- Use views to compare, not as causal claims. Different days, topics and audiences confound them; say "correlation" when you report a lift.
- Free-lane research reports are leads. Spot-check at least one key metric yourself (`twitter tweet <id>`) before the owner sees it.
- Every frame sheet goes through vision review. A cut whose first 3 s is blank or a brand card fails regardless of polish later.
