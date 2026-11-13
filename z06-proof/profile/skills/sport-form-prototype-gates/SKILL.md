---
name: sport-form-prototype-gates
description: Use when prototyping sport pose-feedback loops.
version: 0.1.0
author: Kevin Rajan (kvnloo), Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [sports, pose, feedback, evidence]
    related_skills: []
---

# Sport pose-feedback prototype gates

## When to use

Use for a local video-to-pose, repetition comparison and coaching-replay demonstrator. Do not treat this workflow as participant efficacy, biomechanical or physical-device certification.

## Procedure

1. Read the current goal/evidence/world contracts before implementation. Keep image-plane pose estimates separate from raw sensor observations and simulation; refuse a metric world adapter when depth, calibration, velocity or required forces are unavailable. Never zero-fill unknown physics fields.
2. Check GPU availability with `terminal`, respect existing processes and shared locks, and create a dedicated project-local uv environment on the artifact volume. Assert CUDA availability and use an explicit device; preserve package versions, weight/source hashes, warmup and cold-start receipts.
3. Retrieve a clearly licensed input and the exact file's license page. Preserve creator, source URL, license URL, permitted changes and attribution in a media manifest and playback. A website's general license does not establish media rights or participant biometric consent.
4. Run the real model, retaining per-frame coordinates, confidence, frame/event times and provenance. Treat detector confidence as uncalibrated unless evaluated. Largest-person selection is not an identity tracker.
5. Propose repetitions automatically, then use `vision_analyze` on multi-phase contact sheets, not merely peak frames. A backhand backswing can resemble a forehand follow-through in wrist coordinates. Add explicit phase prerequisites or abstain, and label same-clip tuning separately from held-out accuracy.
6. Compare compatible tasks/views/handedness with confidence-weighted, phase-bounded joint-angle DTW. Preserve timing differences; unrestricted warping can conceal an important error. Reference-self comparison is tautological, and arbitrary resemblance indices are not athlete skill scores.
7. Label assumed-noise perturbation results sensitivity ranges, not calibrated confidence intervals. Independent perturbations can make a self-comparison's sensitivity nonzero. Include view/phase/model limitations and an abstain path.
8. Render side-by-side replay with skeleton, reference role, minimal cue text, uncertainty, source attribution and OFFLINE/RESEARCH labels. Inspect multiple final screenshots; reject clipped text, wrong-person skeletons or misleading phase labels.
9. Measure one continuous decode-to-output processing pass with GPU synchronization, data transfer, analysis events, render and encoder backpressure. Report p50/p95/p99/max and full wall throughput, not only network FPS or separately summed stage proxies. Preserve completion-event spikes instead of hiding them in averages.
10. Separate local-file processing from capture-to-photon latency. Offline smoothing, peak prominence and complete-rep DTW are noncausal; mark known boundaries/reference honestly. Put expensive scoring/sensitivity off the preview thread before testing live feedback, and cue between repetitions first.
11. Keep intention, authority and device examples explicitly MOCK unless a real person supplied goals/approvals. Exercise deny-before-approval, approved dry-run, expiry/revocation and cross-purpose/subject rejection. A toy boolean guard is not production authorization or an emergency stop. Do not execute hardware from a pose demo.
12. Verify executable behavior with tests, parse generated JSON/counts programmatically, fully decode MP4s with FFmpeg, and check exact model/media hashes. Preserve the current schema snapshot and source citations; no pose-quality or learning-effect claims without the corresponding ground truth or trial.

## Evidence review pitfalls

- Distinguish COCO AP, tracking F1, joint-angle error, user satisfaction and feedback-free retained skill. They answer different questions.
- Review motor-learning meta-analyses and publication-bias reanalyses together. Guidance-hypothesis and external-focus benefits are not universal laws.
- Use a strong-coach plus ordinary-video comparator with equal practice/contact time, delayed feedback-off retention and transfer tests. If personalized feedback does not beat the standard, prefer the standard.
- Check implementation, checkpoint, dataset, reference-motion and likeness/consent rights separately. An open repository is not blanket permission to scrape broadcasts or deploy a proprietary service.

## Verification

Deliver code that ran, exact output paths, real latency/test receipts, inspected frames, documented failures and a statement that no participant learning gain was measured unless it actually was. A plausible avatar or fast network alone never closes the learning loop.
