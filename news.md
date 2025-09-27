---
layout: default
title: "News and Other Miscellaneous Happenings"
permalink: /news/
---

# News

{% if site.posts and site.posts.size > 0 %}
{% for post in site.posts %}
- [{{ post.title }}]({{ post.url | relative_url }})  
  *{{ post.date | date: "%B %-d, %Y" }}*  
  {{ post.excerpt | strip_html | strip_newlines | truncate: 300 }}
  {% if post.tags and post.tags.size > 0 %} — _{{ post.tags | join: ", " }}_{% endif %}
  {% if post.excerpt != post.content %} [Read more →]({{ post.url | relative_url }}){% endif %}
{% endfor %}
{% else %}
_No posts yet. Check back soon!_
{% endif %}
