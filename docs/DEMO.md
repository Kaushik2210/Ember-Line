# Demo checklist

## Before you go on (10 minutes)

- [ ] `.env` has a valid `FIRMS_MAP_KEY`; `curl localhost:8000/api/health` answers.
- [ ] `curl localhost:8000/api/showcase` shows Punjab and Haryana `ready`. Note which other regions are
      `ready`: only those show numbers in the atlas. Do not demo a region that says "not downloaded".
- [ ] Open `/explore?r=punjab-haryana` once so the result is cached; the first run can take a minute.
- [ ] Network works for NASA GIBS imagery (map base layer). If the venue Wi-Fi blocks it, the map is blank:
      have the screenshots in `web/qa-screenshots/` ready (run `npm run e2e` to regenerate).
- [ ] Browser at 100% zoom, dark theme, window at least 1280 wide. Close other tabs.
- [ ] Re-read the numbers in `docs/PITCH.md` against the landing page.
- [ ] Team names and license: still to be added (see README).

## 90-second golden path

1. **Landing (0:00-0:15).** Headline, the three computed statistics, the source line under them.
2. **Explore the record (0:15-0:30).** Click it. The workspace opens on Punjab and Haryana, at the busiest
   day, with the calendar drawn.
3. **Compare (0:30-0:45).** Drag the slider across the map: MODIS amber on one side, VIIRS blue on the other.
4. **Calendar (0:45-1:00).** Switch Raw MODIS, Raw VIIRS, Harmonized. The step at 2012 is the point.
5. **Agreement (1:00-1:15).** Sensor agreement tab: before and after scatter, bias -41% to +1%.
6. **Unusual periods (1:15-1:25).** The 2024-25 season; the season ranking.
7. **Share (1:25-1:30).** Share button, paste the link in a new tab: same view.

## If something goes wrong

| Symptom | Do this |
|---|---|
| Landing shows no statistics | API is down or computing; the page says so. Wait or restart the API. |
| Map is blank | GIBS unreachable. Continue on the charts; they do not need it. |
| Run is slow | A region not yet cached is being computed; use Punjab and Haryana, which is prepared. |
| Region says not downloaded | Skip it; do not describe its numbers. |
