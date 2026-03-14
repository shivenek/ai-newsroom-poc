#!/usr/bin/env python3
"""
AI Newsroom Publisher — Baut statische HTML aus Pipeline-Output.
Liest: /review/ (JSONs), /production/drafts/ (MDs), /assets/ (Bilder)
Schreibt: /published/ (HTML + Assets)
"""

import json, os, glob, shutil, re, subprocess
from datetime import datetime, date

BASE = "/Users/denizschwenk/newsroom"
REVIEW = f"{BASE}/review"
DRAFTS = f"{BASE}/production/drafts"
ASSETS_SRC = f"{BASE}/assets"
PUB = f"{BASE}/published"
PUB_ARTICLES = f"{PUB}/articles"
PUB_ASSETS = f"{PUB}/assets"

def load_articles():
    """Lade alle Artikel aus review/ + drafts/"""
    articles = []
    for jf in sorted(glob.glob(f"{REVIEW}/*.json")):
        with open(jf) as f:
            meta = json.load(f)
        aid = meta["id"]
        # Drafts are named {id}-{slug}.md — find by prefix
        md_matches = glob.glob(f"{DRAFTS}/{aid}*.md")
        md_path = md_matches[0] if md_matches else f"{DRAFTS}/{aid}.md"
        body_html = ""
        teaser = ""
        if os.path.exists(md_path):
            with open(md_path) as f:
                md_text = f.read()
            # Frontmatter entfernen
            parts = md_text.split("---", 2)
            if len(parts) >= 3:
                md_body = parts[2].strip()
            else:
                md_body = md_text
            # Teaser = erster fetter Absatz
            teaser_match = re.match(r"\*\*(.+?)\*\*", md_body)
            if teaser_match:
                teaser = teaser_match.group(1)
            body_html = md_to_html(md_body)
        articles.append({
            "id": aid,
            "title": meta.get("title", "Ohne Titel"),
            "teaser": teaser,
            "ressort": meta.get("ressort", "tech-trends"),
            "author": meta.get("author", "AI Newsroom"),
            "date": meta.get("submission_date", datetime.now().isoformat())[:10],
            "keywords": meta.get("keywords", []),
            "body_html": body_html,
            "image": find_image(meta),
        })
    return articles

def md_to_html(md):
    """Einfacher Markdown→HTML Konverter"""
    lines = md.split("\n")
    html = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("## "):
            html.append(f'<h2>{line[3:]}</h2>')
        elif line.startswith("**") and line.endswith("**"):
            html.append(f'<p class="teaser"><em>{line[2:-2]}</em></p>')
        else:
            # Bold
            line = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
            # Italic
            line = re.sub(r"\*(.+?)\*", r"<em>\1</em>", line)
            html.append(f"<p>{line}</p>")
    return "\n".join(html)

def find_image(meta):
    """Versuche ein passendes Bild aus assets/ zu finden"""
    aid = meta.get("id", "")
    # 1. Exakter Match: header-{id}.png
    exact = f"{ASSETS_SRC}/header-{aid}.png"
    if os.path.exists(exact):
        return f"header-{aid}.png"
    # 2. Keyword-Fallback
    images = glob.glob(f"{ASSETS_SRC}/*.png") + glob.glob(f"{ASSETS_SRC}/*.jpg")
    title_lower = meta.get("title", "").lower()
    keywords = [k.lower() for k in meta.get("keywords", [])]
    for img in images:
        fname = os.path.basename(img).lower()
        for kw in keywords:
            if kw.replace(" ", "-") in fname or kw.replace(" ", "_") in fname:
                return os.path.basename(img)
        for word in title_lower.split():
            if len(word) > 4 and word in fname:
                return os.path.basename(img)
    if images:
        return os.path.basename(images[0])
    return None

def build_article_html(article):
    img_tag = ""
    if article["image"]:
        img_tag = f'<img src="../assets/{article["image"]}" alt="{article["title"]}" class="hero-image">\n<span class="photo-credit">Business Punk by KI</span>'

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{article["title"]} – BP AI Newsroom POC</title>
    <link rel="stylesheet" href="../style.css">
</head>
<body>
    <header>
        <nav>
            <a href="../index.html" class="logo">BP <span class="ai-badge">AI Newsroom POC</span></a>
            <span class="ressort-tag">{article["ressort"].replace("-", " & ").title()}</span>
        </nav>
    </header>
    <article>
        {img_tag}
        <div class="article-meta">
            <time>{article["date"]}</time>
            <span class="author">{article["author"]}</span>
        </div>
        <h1>{article["title"]}</h1>
        {f'<p class="teaser"><em>{article["teaser"]}</em></p>' if article["teaser"] else ""}
        <div class="article-body">
            {article["body_html"]}
        </div>
        <div class="keywords">
            {" ".join(f'<span class="tag">{k}</span>' for k in article["keywords"])}
        </div>
    </article>
    <footer>
        <a href="../index.html">← Zurück zur Übersicht</a>
        <p>BP AI Newsroom POC – Automatisch generiert</p>
    </footer>
</body>
</html>"""

def build_index_html(articles):
    today = date.today().strftime("%d. %B %Y")
    # Hero = erster Artikel
    hero = articles[0] if articles else None
    hero_html = ""
    if hero:
        hero_img = f'<img src="assets/{hero["image"]}" alt="{hero["title"]}">' if hero["image"] else ""
        hero_html = f"""
        <section class="hero">
            <a href="articles/{hero["id"]}.html">
                {hero_img}
                <div class="hero-overlay">
                    <span class="ressort-tag">{hero["ressort"].replace("-", " & ").title()}</span>
                    <h2>{hero["title"]}</h2>
                    <p>{hero["teaser"][:160]}...</p>
                </div>
            </a>
        </section>"""

    cards = ""
    for a in articles[1:]:
        img = f'<img src="assets/{a["image"]}" alt="{a["title"]}">' if a["image"] else ""
        cards += f"""
            <a href="articles/{a["id"]}.html" class="card">
                {img}
                <div class="card-body">
                    <span class="ressort-tag">{a["ressort"].replace("-", " & ").title()}</span>
                    <h3>{a["title"]}</h3>
                    <p>{a["teaser"][:120]}...</p>
                </div>
            </a>"""

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tech & Trends – BP AI Newsroom POC</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <header>
        <nav>
            <span class="logo">BP <span class="ai-badge">AI Newsroom POC</span></span>
            <span class="edition">Ausgabe {today}</span>
        </nav>
    </header>
    <main>
        <h1 class="section-title">Tech & Trends</h1>
        {hero_html}
        <section class="grid">
            {cards}
        </section>
    </main>
    <footer>
        <p>BP AI Newsroom POC – Automatisch generiert am {today}</p>
        <p>Powered by Independent Newsroom Harness + Opensource kimi-k2.5 and GLM-5</p>
    </footer>
</body>
</html>"""

def copy_assets():
    for f in glob.glob(f"{ASSETS_SRC}/*"):
        shutil.copy2(f, PUB_ASSETS)

def git_commit_and_tag():
    today = date.today().isoformat()
    os.chdir(PUB)
    subprocess.run(["git", "add", "-A"], check=True)
    result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if not result.stdout.strip():
        print("Keine Änderungen zum committen.")
        return
    subprocess.run(["git", "commit", "-m", f"Publish {today}"], check=True)
    # Tag setzen (falls schon existiert: überschreiben)
    subprocess.run(["git", "tag", "-f", today], check=True)
    print(f"✅ Committed und getaggt: {today}")
    # Push to GitHub Pages
    push = subprocess.run(["git", "push", "origin", "main", "--tags", "--force"], capture_output=True, text=True)
    if push.returncode == 0:
        print("🚀 Gepusht auf GitHub Pages")
    else:
        print(f"⚠️  Push fehlgeschlagen: {push.stderr.strip()}")

def main():
    print("📰 AI Newsroom Publisher")
    print("========================")

    articles = load_articles()
    print(f"📄 {len(articles)} Artikel geladen")

    copy_assets()
    print(f"🖼️  Assets kopiert")

    for a in articles:
        html = build_article_html(a)
        path = f"{PUB_ARTICLES}/{a['id']}.html"
        with open(path, "w") as f:
            f.write(html)
    print(f"📝 {len(articles)} Artikel-HTMLs generiert")

    index = build_index_html(articles)
    with open(f"{PUB}/index.html", "w") as f:
        f.write(index)
    print("🏠 Index generiert")

    git_commit_and_tag()

if __name__ == "__main__":
    main()

