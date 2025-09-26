import matplotlib.pyplot as plt
from io import BytesIO

def pie_chart_by_category(breakdown: dict, title: str) -> BytesIO:
    labels = list(breakdown.keys())
    values = [v/100 for v in breakdown.values()]  # convert cents → dollars
    if not values:
        values = [0]
        labels = ["No Data"]

    fig, ax = plt.subplots(figsize=(6,6))
    ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
    ax.set_title(title)
    buf = BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close(fig)
    return buf

def bar_chart_by_month(month_totals: dict, title: str) -> BytesIO:
    months = [f"{m:02d}" for m in sorted(month_totals.keys())]
    values = [month_totals[m]/100 for m in sorted(month_totals.keys())]

    fig, ax = plt.subplots(figsize=(8,5))
    ax.bar(months, values, color="skyblue")
    ax.set_title(title)
    ax.set_xlabel("Month")
    ax.set_ylabel("Amount ($)")
    buf = BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close(fig)
    return buf
