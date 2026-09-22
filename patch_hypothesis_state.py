import os

dash_path = "static/dashboard.html"
with open(dash_path, "r", encoding="utf-8") as f:
    content = f.read()

old_code = """    const data = await r.json();
    renderHypothesis(data.hypothesis);"""

new_code = """    const data = await r.json();
    DATA.llm_hypothesis = data.hypothesis;
    renderHypothesis(data.hypothesis);"""

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(dash_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Dashboard state fixed.")
else:
    print("Could not find the target code in dashboard.html. It might already be patched.")

