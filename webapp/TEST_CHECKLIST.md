# Web Application Test Checklist

## Pre-Launch Testing

### Initial Load
- [ ] Page loads in < 5 seconds
- [ ] Map displays with interpolated heatmap
- [ ] Map shows all 9,892 points (smooth gradient)
- [ ] No time series panel visible initially
- [ ] Controls panel displays correctly
- [ ] Legend overlay shows on map
- [ ] No console errors

### Map Interactions
- [ ] Hover over map → tooltip appears with point details
- [ ] Hover away → tooltip disappears
- [ ] Click point → time series panel slides in from right
- [ ] Selection marker appears (white dashed circle)
- [ ] Point remains highlighted
- [ ] Map resizes to 50% width (desktop)

### Time Series Panel
- [ ] Loads within 5-10 seconds on first click
- [ ] Chart displays P, ETP, Stock, Gap
- [ ] Summer periods highlighted (when season = all)
- [ ] Hover over chart → vertical line and tooltip
- [ ] Statistics panel shows 8 metrics
- [ ] All data appears correctly formatted

### Controls
- [ ] Metric selector: Switch between Stock/Gap → map updates
- [ ] Year filter: Select 2020 → only 2020 data shown
- [ ] Season filter: Select Summer → other seasons are hatched
- [ ] Close button: Click ✕ → time series hides, map full width

### Series Toggles
- [ ] Uncheck P → precipitation bars disappear
- [ ] Uncheck ETP → orange line disappears
- [ ] Uncheck Stock → blue line disappears
- [ ] Uncheck Gap → red area disappears
- [ ] Check all → all series reappear

### Season Gap Visualization
- [ ] Select "Summer" → hatched rectangles appear for non-summer months
- [ ] Hatching has diagonal lines
- [ ] "Excluded" labels visible on large gaps
- [ ] Switch to "All Seasons" → hatching disappears, summer highlights appear

### Performance
- [ ] Initial map render < 1 second
- [ ] Hover interactions smooth (60 FPS)
- [ ] Filter changes apply within 100ms
- [ ] Panel transitions smooth (400ms)
- [ ] No memory leaks after 10+ point clicks
- [ ] Browser doesn't freeze or crash

### Responsive Design
- [ ] Desktop (1920x1080): Full layout works
- [ ] Laptop (1366x768): Scales appropriately
- [ ] Tablet (768x1024): Vertical stack layout
- [ ] Mobile (375x667): Controls stack, readable
- [ ] Legend stays visible on all sizes

### Visual Quality
- [ ] Interpolation is smooth (no pixelation)
- [ ] Color gradients look professional
- [ ] Typography is readable
- [ ] Shadows and effects render correctly
- [ ] Animations are smooth
- [ ] No flickering or jumping

### Data Accuracy
- [ ] Tooltip values match expected ranges
- [ ] Statistics calculations are correct
- [ ] Time series shows correct date range
- [ ] Filters produce expected results
- [ ] Gap formula applied correctly

### Browser Compatibility
- [ ] Chrome 90+
- [ ] Firefox 88+
- [ ] Safari 14+
- [ ] Edge 90+

### Error Handling
- [ ] Network error → shows error message
- [ ] Invalid point click → doesn't crash
- [ ] Missing data → handles gracefully
- [ ] Console shows meaningful errors (if any)

## Known Issues to Watch For

### Potential Problems
1. **First data load (3.3 GB)**
   - May take 5-30 seconds depending on connection
   - Browser may show "unresponsive script" warning
   - Solution: Wait, data is cached after first load

2. **Memory usage**
   - With all data loaded, uses ~1 GB RAM
   - Older devices may struggle
   - Consider closing other tabs

3. **Interpolation performance**
   - 50x50 grid with 9,892 points
   - Each cell calculates 5 nearest neighbors
   - May be slow on older devices
   - Consider reducing grid resolution if needed

4. **Mobile experience**
   - Best on desktop/tablet
   - Mobile may be cramped
   - Touch interactions work but not optimized

## Testing Commands

```bash
# Start server
cd webapp
python -m http.server 8000

# Check file sizes
ls -lh data/*.json

# Monitor console
# Open browser DevTools (F12) → Console tab
# Watch for errors or warnings
```

## Performance Monitoring

Open browser DevTools → Performance tab:
1. Click "Record"
2. Interact with app (hover, click, filter)
3. Stop recording
4. Check:
   - FPS should be 60 (green)
   - No long tasks (> 50ms)
   - Memory usage stable

## Accessibility Check

- [ ] Keyboard navigation works
- [ ] Focus indicators visible
- [ ] Labels on all controls
- [ ] Color contrast meets WCAG AA
- [ ] Screen reader compatible (basic)

## Final Checks

- [ ] All features from plan implemented
- [ ] Documentation complete
- [ ] No TODO comments in code
- [ ] Console is clean (no errors)
- [ ] Ready for demo/presentation

## Success Criteria

✅ **Passed if:**
- Initial load < 5 seconds
- Smooth interpolated map
- Dynamic layout works
- Season gaps display correctly
- Modern design looks professional
- No critical bugs

❌ **Failed if:**
- Page doesn't load
- Map shows discrete circles (not interpolated)
- Time series doesn't appear on click
- Season filter doesn't show gaps
- Console full of errors

## Notes

- First point click will be slow (loading 3.3 GB)
- This is expected and acceptable
- Subsequent clicks should be fast (cached)
- Consider optimizing in future with server API

---

**Test Date:** _______  
**Tester:** _______  
**Result:** ⬜ Pass | ⬜ Fail  
**Notes:** __________________
