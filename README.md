# 🧼 Bravo Maids Media Center — Automated Builder

This repository contains the **Bravo Maids Media Center Builder**, a small but powerful system that turns a JSON blueprint into a fully structured “Media Center” folder for the Bravo Maids brand — with automatic versioning and ZIP packaging.

It’s designed so that:

- Locally (on your Mac), you can run a single Python command and get a fresh, versioned Media Center folder + ZIP.
- In GitHub, you can click **“Run workflow”** and have GitHub Actions build and package the Media Center for you, then store the ZIP as a downloadable artifact (and optionally a Release).

---

## 🔧 Core Pieces

### 1. `structure_fixed.json`

- This file is the **blueprint** for the entire Media Center.
- The top-level key is the root folder name, e.g.:

  ```json
  {
    "Bravo_Maids_Media_Center": {
      "1.0_SYSTEM_INFRASTRUCTURE": {
        "README.md": "# 1.0 SYSTEM INFRASTRUCTURE\nSystem-level setup, folder logic, automation wiring.\n"
      },
      "2.0_CREATIVE_GENERATOR": {
        "README.md": "# 2.0 CREATIVE GENERATOR\nPrompts, templates, creative workflows.\n"
      },
      "3.0_META_AD_ENGINE": {
        "README.md": "# 3.0 META AD ENGINE\nMeta ads batch structure, automation stages.\n"
      },
      "4.0_SOCIAL_MEDIA_AUTOPILOT": {
        "README.md": "# 4.0 SOCIAL MEDIA AUTOPILOT\nFB/IG/LinkedIn auto-post scheduling system.\n"
      },
      "5.0_WEBSITE_CONTENT_ENGINE": {
        "README.md": "# 5.0 WEBSITE CONTENT ENGINE\nSEO blogs, landing page automation.\n"
      },
      "6.0_SEO_RESEARCH_ENGINE": {
        "README.md": "# 6.0 SEO RESEARCH ENGINE\nKeyword mining, SERP analysis, competitor mapping.\n"
      },
      "7.0_EMAIL_SALES_ENGINE": {
        "README.md": "# 7.0 EMAIL SALES ENGINE\nConvertKit sequences and email automations.\n"
      },
      "8.0_VIDEO_SORA_ENGINE": {
        "README.md": "# 8.0 VIDEO SORA ENGINE\nSora video prompts + workflow automation.\n"
      },
      "9.0_CLEANER_OUTREACH_ENGINE": {
        "README.md": "# 9.0 CLEANER OUTREACH ENGINE\nRecruiting campaigns, gig outreach funnels.\n"
      }
    }
  }
