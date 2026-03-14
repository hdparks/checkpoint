# Checkpoint - Development Roadmap

## Phase 1: Quick Wins (Done ✅)
- [x] Add dark mode toggle to web dashboard
- [x] Replace `/skip` command with inline "Skip note" button
- [x] Add delete entry functionality in web UI

## Phase 2: Data & Analytics (Done ✅)
- [x] Add mood distribution pie chart
- [x] Weekly/monthly summary reports
- [x] "Insights" feature (correlate mood with days of week)
- [x] CSV/JSON data export

## Phase 3: Multi-user Support (Done ✅)
- [x] Add user filter dropdown on dashboard
- [x] Per-user dashboard views
- [x] User authentication (optional)

## Phase 4: Enhanced Engagement
- [ ] Streak protection alerts (notify before streak breaks)
- [ ] Scheduled reminders (specific times, not just random)
- [ ] Activity/tags for entries (work, exercise, sleep, etc.)
- [ ] Browser push notifications for web dashboard

## Phase 5: Bot Intelligence
- [ ] Quick reply templates for notes
- [ ] Daily/weekly summary from bot

## Phase 6: PWA & Mobile
- [ ] Convert web dashboard to PWA
- [ ] Add manifest.json and service worker
- [ ] Mobile-optimized UI improvements

# Bugs
- [x] /interval bot command is not persisting
- [x] /pinghours is not persisting
- [x] manually hitting /mood doesn't seem to be updating the "last recorded mood" state. I just got a scheduled ping a few minutes after hitting a manual mood
