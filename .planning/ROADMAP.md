# Roadmap: The Holding Cell

## Milestones

- ✅ **v1.0 MVP** - Phases 1-5 shipped 2026-03-04 ([archive](./milestones/v1.0-ROADMAP.md))
- 🚧 **v1.1 UI Polish** - Phases 6-9 planned

## Overview

Milestone v1.1 delivers a medium-fidelity, mockup-inspired UI-polish pass that improves command-center visual identity, threat-signal hierarchy, interaction clarity, and responsive accessibility without changing backend contracts or realtime semantics.

## Phases

- [ ] **Phase 6: Command-Center Visual Foundation** - Establish mockup-inspired shell, grid framing, and readable retro-neon visual system across core surfaces.
- [ ] **Phase 7: Live Surface Threat Hierarchy** - Make KPI strip, Live Cell Block, and Prisoner File surfaces severity-forward and scan-efficient.
- [ ] **Phase 8: Interaction and Realtime Feedback Polish** - Complete interaction/system-state feedback and restrained motion across live dashboard widgets.
- [ ] **Phase 9: Responsive Accessibility Hardening** - Ensure desktop/mobile command workflow integrity, keyboard focus visibility, and readable contrast.

## Phase Details

### Phase 6: Command-Center Visual Foundation
**Goal**: Users experience one coherent, mockup-inspired command-center shell and visual system that remains readable in dense analyst workflows while preserving v1.0 behavior contracts.
**Depends on**: Phase 5 (v1.0 shipped baseline)
**Requirements**: VIS-01, VIS-02, VIS-03, VIS-04
**Success Criteria** (what must be TRUE):
  1. User can see one consistent retro-neon command-center language across top nav, KPI strip, live panels, and archive surfaces.
  2. User can read dense dashboard data with legible retro typography, spacing, and contrast tuned for scanning.
  3. User can distinguish primary interface sections through consistent grid alignment, panel framing, and heading patterns.
  4. User can use the polished dashboard without any visible change to existing backend data behavior or realtime semantics.
**Plans**: 3 total (06-01 complete, 06-02 and 06-03 pending)

### Phase 7: Live Surface Threat Hierarchy
**Goal**: Users can triage highest-risk threats first because severity and recency cues are consistently prioritized across KPI, Live Cell Block, and Prisoner File surfaces.
**Depends on**: Phase 6
**Requirements**: HIER-01, HIER-02, HIER-03
**Success Criteria** (what must be TRUE):
  1. User can identify highest-severity threats first from KPI strip and primary dashboard surfaces.
  2. User can scan Live Cell Block and Prisoner File regions with consistent severity and recency emphasis.
  3. User can prioritize investigation targets faster because critical signals are visually distinct across cards, bars, and rows.
**Plans**: TBD

### Phase 8: Interaction and Realtime Feedback Polish
**Goal**: Users receive clear, reliable UI feedback for interactive and system states across live widgets without disruptive animation during realtime updates.
**Depends on**: Phase 7
**Requirements**: STATE-01, STATE-02, STATE-03, STATE-04
**Success Criteria** (what must be TRUE):
  1. User can reliably perceive hover, focus, and selected states on nav elements, action controls, and data rows.
  2. User can understand loading, error, empty, and disconnected states across live and archive surfaces.
  3. User with reduced-motion preferences can still understand state changes without relying on heavy motion.
  4. User can observe realtime updates in status/metrics/live surfaces with restrained transitions that avoid distraction.
**Plans**: TBD

### Phase 9: Responsive Accessibility Hardening
**Goal**: Users can complete core command-center workflows on desktop and mobile with accessible readability and keyboard navigation.
**Depends on**: Phase 8
**Requirements**: RESP-01, RESP-02, RESP-03, RESP-04
**Success Criteria** (what must be TRUE):
  1. User can complete command workflows on desktop without clipped or overlapping controls in the two-column command-center layout.
  2. User can complete command workflows on common mobile widths with intentional panel stacking and readable density.
  3. User can navigate interactive elements with visible keyboard focus indicators.
  4. User can read critical dashboard information in the neon theme with contrast and readability that meet accessibility expectations.
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 6. Command-Center Visual Foundation | 1/3 | In Progress | - |
| 7. Live Surface Threat Hierarchy | 0/TBD | Not started | - |
| 8. Interaction and Realtime Feedback Polish | 0/TBD | Not started | - |
| 9. Responsive Accessibility Hardening | 0/TBD | Not started | - |
