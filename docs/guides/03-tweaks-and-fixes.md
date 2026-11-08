# 3. Tweaks and fixes

Use this page to look things up when you need them. Every setting updates the
preview straight away, so the quickest way to learn a setting is to change it
and watch the chart.

## "I want to…"

| I want to… | Where | What to do |
|---|---|---|
| Break the title onto two lines | Text | Press **Enter** inside **Title** |
| Thin out crowded x-axis labels | Axes | Set **Max x ticks**, for example `5`, or set an **X tick step** |
| Label every year | Axes | **X tick step** `1` |
| Show months as *Jan 24* | Axes | **X date format** `%b %y` |
| Show years only on a monthly chart | Axes | **X date format** `%Y` together with **Year tick interval (line)** `1` |
| Add a small tick between labels | Axes | **X minor ticks per interval** `1` (for example, mid-year) |
| Write `'21` instead of `2021` | Chart | Tick **Compact years** |
| Tilt long x labels | Chart | **X label rotation**, for example `45` |
| Cut or wrap long category names | Layout | **Max label width (chars)** plus **Long labels**: `wrap` or `truncate` |
| Show values as `12%` | Axes | **Value format** `Percent`. The data must be fractions, so 0.12 shows as 12% |
| Show values as `1,234.5` | Axes | **Value format** `Custom` with format string `{x:,.1f}` |
| Start the y-axis at zero, or fix its range | Axes | **Y min** and **Y max**. Fill in both, or neither |
| Print numbers on the bars or points | Chart | Tick **Value labels** |
| Hide the y-axis numbers and gridlines | Layout | Untick **Show y gridlines + labels**. This works well together with value labels |
| Put y labels on the left | Layout | **Y-axis side** `left` |
| Change all colours at once | Colors | **Theme** |
| Give one series a fixed colour | Colors | Change that series from `auto` to a role or to **custom** |
| Make one series fainter | Colors | Lower its **Opacity** |
| Change the legend layout | Legend | **Legend columns** |
| Remove or replace the footer logo | Layout | **Footer logo**: `Off`, or `Custom` and upload an image |
| Remove the whole footer | Layout | Untick **Footer (rule, caption, logo)** |
| Add space after the last data point | Layout | **X upper pad**, for example `0.05` for 5% of the data range |

Any number box that shows **auto** works out a good value on its own. To go
back to automatic, clear the box.

## Themes

| Theme | Background | Good for |
|---|---|---|
| `newsroom_dark` | Near-black | Social media, the default look |
| `consulting_dark` | Dark navy | Presentations with dark slides |
| `newsroom_muted` | Off-white | Reports, multi-colour comparisons |
| `consulting_light` | White | Documents, a clean single-colour look |

The first series always gets the theme's **primary** colour, the second gets
**secondary**, and so on.

## Problems and fixes

| What you see | Why | Fix |
|---|---|---|
| A red message on a reshape step | That step can't run. Usually a column it uses has disappeared, for example after a Group or Pivot. | Read the message. A column marked **⚠ (missing)** needs a new choice. The steps after it are skipped until you fix it. |
| Strange totals such as `6066` for Year | A **Group** step added up the `Year` column too | In that step, choose **Value columns** explicitly |
| Bars or lines stacked on top of each other, wrong-looking chart | There are still several rows per x value | Add a **Group + aggregate** step, or a **Pivot** for one column per group |
| Dates show as plain text labels | The column isn't stored as a date | In CSV files, write dates as `2024-03-01`. In Excel, format the cells as dates. |
| "Series column(s) must be numeric" | A number column contains text, such as `n/a` or `1,234` | Clean the file, or filter those rows out |
| "There is no data to plot" | A filter removed every row | Check the filter's spelling and capital letters. `=` must match exactly. |
| The legend is missing | There's only one series. This is on purpose: the subtitle names it. | Add more series, or describe the one series in the subtitle |
| Long names are cut off | The label is too long for the space | Shorten it with **Max label width**, or on bump charts use **Label text** with `\n` |
| MMA **Fetch** fails | The token is missing, or the series number is wrong | Set `MMA_API_TOKEN` or put the token in `TOKEN.txt`, then check the series number |
| The app is slow | The data is very large | Filter or group it early, near the top of the steps |

**Next:** [4. Charts in Python →](04-charts-in-python.md)
