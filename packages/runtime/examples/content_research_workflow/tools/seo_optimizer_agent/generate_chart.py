"""
Generate Chart Tool - SEO Optimizer Agent (Code Mode).
"""

from framework.agents.tool import tool


@tool(
    name="generate_chart",
    description="Generate Python code for creating a chart. Returns matplotlib code that can be executed.",
)
async def generate_chart(data: dict, chart_type: str = "bar") -> str:
    """
    Generate chart code.

    Args:
        data: Dictionary with data to visualize (e.g., {"python": 10, "ai": 8})
        chart_type: Type of chart - "bar", "line", "pie" (default: "bar")

    Returns:
        Python code string for generating the chart
    """
    chart_type = chart_type.lower()

    if chart_type == "bar":
        code = f"""import matplotlib.pyplot as plt

data = {data}
plt.figure(figsize=(10, 6))
plt.bar(data.keys(), data.values())
plt.xlabel('Categories')
plt.ylabel('Values')
plt.title('Bar Chart')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
"""
    elif chart_type == "line":
        code = f"""import matplotlib.pyplot as plt

data = {data}
plt.figure(figsize=(10, 6))
plt.plot(list(data.keys()), list(data.values()), marker='o')
plt.xlabel('Categories')
plt.ylabel('Values')
plt.title('Line Chart')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
"""
    elif chart_type == "pie":
        code = f"""import matplotlib.pyplot as plt

data = {data}
plt.figure(figsize=(8, 8))
plt.pie(data.values(), labels=data.keys(), autopct='%1.1f%%')
plt.title('Pie Chart')
plt.show()
"""
    else:
        code = f"""# Unsupported chart type: {chart_type}
# Defaulting to bar chart
import matplotlib.pyplot as plt

data = {data}
plt.figure(figsize=(10, 6))
plt.bar(data.keys(), data.values())
plt.xlabel('Categories')
plt.ylabel('Values')
plt.title('Bar Chart')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
"""

    return code
