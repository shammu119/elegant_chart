# 1. Getting started

By the end of this guide you'll have built this chart without writing any code:

<img src="images/recipe_top10_hbar.png" width="320" alt="Top 10 airlines horizontal bar chart">

## Step 1: Install

You need **Python 3.12 or newer**. To check which version you have, run:

```bash
python3 --version
```

Then, from the `elegant_chart` folder, install the library together with the app:

```bash
pip install -e ".[app]"
```

You only need to do this once. When you get new code from GitHub later, run
the command again in case anything new needs installing.

## Step 2: Open Chart Studio

```bash
elegant-chart-studio
```

Your web browser opens a page at `http://localhost:8501`. The app runs on your
own computer, so nothing is uploaded anywhere.

To close the app, go back to the terminal and press `Ctrl + C`.

> **Browser didn't open?** Copy the `Local URL` that the terminal prints and
> paste it into your browser.

## Step 3: Learn the screen

![Chart Studio with a finished chart](images/studio_overview.png)

The screen has a toolbar and three panels:

| Part | What it's for |
|---|---|
| **Toolbar** (top) | Pick the **chart type** (Bar, H-bar, Line, Bump), and **Export PNG** or **Data .xlsx**. |
| **Sidebar** (left) | A **progress checklist** that shows what to do next, then your data and the **reshape steps**. A table at the bottom shows the result. |
| **Preview** (centre) | The chart, redrawn about half a second after every change. **What you see is exactly what you download.** |
| **Inspector** (right) | One section at a time: **Chart** (columns and options), **Text**, **Axes**, **Colors**, and **…** (layout and legend). |

**The checklist tells you what's next.** It lists *Data → Chart → Titles →
Look → Export*. A green tick means a step is done, the blue number is your
next step ("Next: add a title so readers know what they see"), and *Look* is
optional. When everything required is done, *Export* says **Ready to export**.

**Settings show you the result before you choose.** Where a setting needs a
format (a date style, a number style), the options are listed with what they
print from *your* data, so you pick by looking, not by remembering codes.
Hover the **?** next to a setting for a short explanation.

## Step 4: Load the data

1. Under **Source**, choose **File**.
2. Drag `examples/data/airlines_sample.csv` into the upload box.

The sidebar shows **42 rows × 4 cols** under the file name. Each row is one airline in one
year, so Emirates appears three times: 2021, 2022 and 2023.

> **Using MMA data instead?** Choose **MMA series**, type the series number and
> click **Fetch**. The app then shows the series name, how often it is
> published and its unit, so you can check you got the right one. It uses the same token as your Python scripts (the
> `MMA_API_TOKEN` setting or a `TOKEN.txt` file), and it never shows the token.

## Step 5: Shape the data with steps

We want one bar per airline: its total international passengers, biggest
first, top 10 only. That takes four steps. For each one, click
**＋ Add step**, pick the step, then fill it in:

| # | Step | Fill in | What it does |
|---|---|---|---|
| 1 | **Filter rows** | Column `Type`, Condition `=`, Value `International` | Keeps only international flights |
| 2 | **Group and total up** | Group by `Airline`, Combine values using `sum`, Columns to combine `Total Passengers` | Adds the three years together, giving one row per airline |
| 3 | **Sort** | Column `Total Passengers`, leave **Smallest first** off | Puts the biggest airline first |
| 4 | **Keep the top rows** | How many rows to keep `10` | Keeps the first 10 rows |

<img src="images/studio_data_panel.png" width="360" alt="The four reshape steps filled in">

Under each step, a small note such as **→ 12 rows** tells you how many rows
are left after it. The table at the bottom shows the final result.

> **Tip:** In step 2, always choose **Columns to combine**. If you leave it empty,
> the app adds up *every* number column, including `Year`, which gives you
> nonsense values like 6066.

## Step 6: Choose the chart

Open the **Chart** section on the right.

1. **Chart type** (in the toolbar): choose **H-bar**. Long airline names are easier to read on the side.
2. **X column**: `Airline` (this is the category for each bar; the app usually picks it for you).
3. **Series**: `Total Passengers`.
4. Tick **Value labels** to print each number at the end of its bar.

<img src="images/studio_chart_tab.png" width="360" alt="Chart tab settings">

## Step 7: Add words

Open the **Text** section:

- **Title**: `Top 10 airlines` then press **Enter** and type `by passengers`.
  Short two-line titles look best.
- **Subtitle**: `International passengers, 2021-23 combined`. Use the subtitle
  to say what is being measured.
- **Caption / source**: `Source: sample data`

## Step 8: Download

Click **Export PNG** in the toolbar to get the finished 1080 × 1350 image, and
**Data .xlsx** to get the numbers behind the chart.

You've made your first chart. 🎉

## Good to know

- **Switching chart type keeps everything.** Try **Bar** or **Line** in the
  toolbar: your data, steps, title and colours all stay.
- **Nothing is saved when you close the app.** Download what you need before
  you close it.
- **If something goes wrong, the app tells you.** A red message appears on the
  step or setting that needs fixing. The app keeps working.

**Next:** [2. Chart recipes →](02-chart-recipes.md)
