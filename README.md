# Blind Hams Network Website

This repository contains the source for the Blind Hams Network website, built with [Jekyll](https://jekyllrb.com/).

## Adding News Posts

News updates are ordinary Jekyll posts stored in the [`_posts/`](./_posts) directory. To ensure that Jekyll recognises a file as a post:

1. Name the file using the standard `YYYY-MM-DD-title.md` pattern.
2. Use a **lowercase** Markdown extension such as `.md` or `.markdown`.

Jekyll only treats files with those lowercase extensions as Markdown posts, so using `.MD` (uppercase) or other variations will prevent the post from appearing on the site.

Each post should start with YAML front matter, for example:

```yaml
---
layout: post
title: "Example Post"
date: 2025-09-27 12:00:00 -0500
---
```

After adding a new post, run `bundle exec jekyll serve` locally (if available) to verify that the homepage and the [News page](./news.md) both show the update.
