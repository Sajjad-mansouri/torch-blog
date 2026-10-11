# Torch

A full-featured blogging platform built with Django and Django REST Framework.

Torch is a complete content platform with three user roles — readers, authors, and editors — and a real editorial workflow from draft to published. Every part of it is written from scratch: no SPA framework, no admin generator, no scaffolding.

---

## Live demo

- **Site:** [https://yourname.pythonanywhere.com](https://torchblog.pythonanywhere.com)
- **API docs (Swagger):** `/api/docs/`
- **API docs (ReDoc):** `/api/redoc/`
- **OpenAPI schema:** `/api/schema/`

---

## What it does

### Reader
- Browse the home page with featured, latest, and trending sections
- Search posts, tags, and authors with live autocomplete
- Filter and sort the post list by category, tag, author, date, and popularity
- Read full posts with rich content, comments, and similar posts
- Like and bookmark posts
- Comment and reply (one level deep)
- View author profiles
- Get notified about replies, likes, and editorial decisions

### Author
- Write posts in a rich-text editor (CKEditor 5)
- Manage drafts, submit for review, and track status
- Attach a featured image, primary and extra categories, and tags
- Set SEO fields: meta title, meta description, `noindex`
- Preview a post exactly as a reader will see it, without counting a view
- See aggregate analytics for all of their own posts
- Every edit is versioned

### Editor
- Review queue with pending posts, oldest first
- Approve, reject, or request changes — each decision carries its own note
- Reconsider — revert an accidental decision and return the post to the queue
- Moderate comments: approve, reject, mark as spam, or delete
- Manage categories and tags (with merge)
- Curate the featured set with drag-and-drop reordering
- Change user roles, ban or unban accounts
- See a full activity log of every editorial action

---

## The editorial workflow

Every post moves through a defined pipeline:

```
draft → pending → approved → published
             ↘ rejected             ↘ unpublished
             ↘ changes_requested    ↘ archived
```

Transitions are methods on the `Post` model. Permissions are classes, not `if` statements. Every decision is recorded with a reviewer, a timestamp, and a reason.

Key design decisions:

- **Reconsider** exists because editors make mistakes. A rejected post can go back to pending with one call.
- **Preview does not count as a view.** The preview endpoint returns the full post but never touches analytics.
- **Soft delete.** Posts are marked deleted instead of removed, so an accidental delete is recoverable.
- **Activity log.** Every action is written with user, target type, target ID, IP, and timestamp.

---

## Roles and permissions

Three roles with three permission tiers:

| Role | Can do |
|---|---|
| Reader | Read, like, bookmark, comment |
| Author | Everything a reader does, plus write and submit posts |
| Editor | Everything an author does, plus review, moderate, curate, and manage users |

Object-level permissions live in a dedicated module:

- `IsAuthorOrEditorOrReadOnly`
- `IsOwnerOrEditor`
- `CanSubmitPost`
- `IsEditor`

Views declare what they need. The permission layer decides.

---

## Tech stack

### Backend
- Python 3.12
- Django 5.2
- Django REST Framework
- SimpleJWT (JWT auth with blacklist)
- drf-spectacular (OpenAPI 3.0 schema, Swagger UI, ReDoc)
- Django CKEditor 5
- Pillow

### Data
- SQLite
- Django ORM with a custom `PostQuerySet`

### Frontend
- HTML5
- CSS3 (design tokens, custom components, no framework)
- Vanilla JavaScript (fetch, no build step)
- CKEditor 5 (UMD build, loaded from CDN)

---

## Project structure

```
torch/
├── config/                 # Django project settings and root URLs
├── accounts/               # Users, roles, JWT auth, profiles
├── blog/                   # Posts, categories, tags, revisions
├── interactions/           # Likes, bookmarks, comments
├── editor/                 # Editorial dashboard API
├── notifications/          # User notifications
├── core/                   # Landing page, contact, activity log, site settings
├── templates/              # All HTML templates
├── static/
│   ├── css/blog/           # Page-specific stylesheets
│   └── js/
│       ├── api.js          # Fetch wrapper with auth + refresh
│       ├── topbar.js       # Topbar auth menu, categories, search
│       ├── search.js       # Live search with autocomplete
│       └── blog/           # Per-page modules
└── manage.py
```

Each app separates its API layer (`api/`) from its domain layer. Models never know they are being serialized.

---

## API overview

Full schema at `/api/schema/`. Highlights:

### Auth
```
POST   /api/v1/auth/register/
POST   /api/v1/auth/login/
POST   /api/v1/auth/logout/
POST   /api/v1/auth/token/refresh/
GET    /api/v1/auth/me/
PATCH  /api/v1/auth/me/
POST   /api/v1/auth/me/avatar/
POST   /api/v1/auth/me/change-password/
POST   /api/v1/auth/password-reset/
POST   /api/v1/auth/password-reset/confirm/
POST   /api/v1/auth/verify-email/confirm/
POST   /api/v1/auth/verify-email/resend/
```

### Public reads
```
GET    /api/v1/home/
GET    /api/v1/posts/
GET    /api/v1/posts/<slug>/
GET    /api/v1/posts/<slug>/comments/
GET    /api/v1/categories/
GET    /api/v1/categories/<slug>/posts/
GET    /api/v1/tags/
GET    /api/v1/tags/<slug>/posts/
GET    /api/v1/authors/
GET    /api/v1/authors/<username>/
GET    /api/v1/search/
GET    /api/v1/search/suggest/
GET    /api/v1/landing/
POST   /api/v1/contact/
```

### Interactions
```
POST   /api/v1/posts/<slug>/like/
POST   /api/v1/posts/<slug>/bookmark/
POST   /api/v1/posts/<slug>/comments/
PATCH  /api/v1/comments/<id>/
DELETE /api/v1/comments/<id>/
POST   /api/v1/comments/<id>/like/
GET    /api/v1/me/likes/
GET    /api/v1/me/bookmarks/
```

### Author
```
POST   /api/v1/dashboard/posts/
GET    /api/v1/dashboard/posts/<slug>/
PATCH  /api/v1/dashboard/posts/<slug>/
DELETE /api/v1/dashboard/posts/<slug>/
POST   /api/v1/dashboard/posts/<slug>/submit/
GET    /api/v1/me/posts/
GET    /api/v1/me/posts/drafts/
GET    /api/v1/me/posts/analytics/
GET    /api/v1/posts/<slug>/preview/
```

### Editor
```
GET    /api/v1/editor/review-queue/
GET    /api/v1/editor/posts-list/
POST   /api/v1/editor/posts/<slug>/approve/
POST   /api/v1/editor/posts/<slug>/reject/
POST   /api/v1/editor/posts/<slug>/request-changes/
POST   /api/v1/editor/posts/<slug>/unpublish/
POST   /api/v1/editor/posts/<slug>/reconsider/
GET    /api/v1/editor/featured/
GET    /api/v1/editor/featured/candidates/
POST   /api/v1/editor/featured/<slug>/add/
DELETE /api/v1/editor/featured/<slug>/remove/
PATCH  /api/v1/editor/featured/reorder/
GET    /api/v1/editor/comments-list/
POST   /api/v1/editor/comments/<id>/approve/
POST   /api/v1/editor/comments/<id>/reject/
POST   /api/v1/editor/comments/<id>/spam/
DELETE /api/v1/editor/comments/<id>/delete/
GET    /api/v1/editor/users-list/
PATCH  /api/v1/editor/users/<id>/role/
POST   /api/v1/editor/users/<id>/ban/
POST   /api/v1/editor/users/<id>/unban/
GET    /api/v1/editor/categories/
POST   /api/v1/editor/categories/
PATCH  /api/v1/editor/categories/<slug>/
DELETE /api/v1/editor/categories/<slug>/
GET    /api/v1/editor/tags/
POST   /api/v1/editor/tags/
PATCH  /api/v1/editor/tags/<slug>/
DELETE /api/v1/editor/tags/<slug>/
POST   /api/v1/editor/tags/merge/
GET    /api/v1/editor/settings/
PATCH  /api/v1/editor/settings/
GET    /api/v1/editor/activity-log/
```

### Notifications
```
GET    /api/v1/notifications/
GET    /api/v1/notifications/<id>/
DELETE /api/v1/notifications/<id>/
POST   /api/v1/notifications/<id>/read/
POST   /api/v1/notifications/read-all/
GET    /api/v1/notifications/unread-count/
DELETE /api/v1/notifications/clear/
```

---

## Frontend pages

- `/` — Landing page (project overview, tech stack, features, API, roadmap, contact)
- `/home/` — Reader home with featured, latest, and trending
- `/posts/` — Post list with filters and search
- `/posts/<slug>/` — Post detail with comments
- `/categories/`, `/categories/<slug>/` — Category browse and detail
- `/tags/`, `/tags/<slug>/` — Tag browse and detail
- `/author/<username>/` — Author profile
- `/search/` — Search results
- `/login/`, `/register/`, password reset, email verification
- `/dashboard/` — Reader dashboard
- `/dashboard/posts/` — Author's posts
- `/dashboard/posts/new/`, `/dashboard/posts/<slug>/edit/` — Post editor
- `/dashboard/posts/<slug>/preview/` — Author/editor preview
- `/editor/` — Editor dashboard (Review Queue, All Posts, Featured, Comments, Users, Taxonomy, Settings, Activity Log)

The frontend is vanilla JavaScript. One module per page, one state object per module, one render path. No global state, no build step, no framework.

---

## Interesting parts

### Caching without Redis
The home page and landing page are cached with Django's default cache backend, invalidated on model save. Aggregate payloads are stored as plain dicts, not querysets, so a cache hit is a single `json.dumps` away from the response.

### Preview does not count as a view
The preview endpoint returns the same payload as the public detail view but never records a view. Authors can look at their work as many times as they want without inflating their own numbers.

### The reconsider action
An editor can move a rejected or changes-requested post back to pending. It clears the rejection note, the reviewer, and the timestamp. The action exists because editors make mistakes and the alternative — asking a developer to flip a row in the database — is worse.

### One API wrapper for the entire frontend
Every page uses the same `apiFetch()` helper. It attaches the access token, retries once on `401` after refreshing, and surfaces DRF field errors as a typed object. No page ever writes raw `fetch` code.

### Design tokens
Every color, radius, shadow, and typeface is defined once and referenced by name everywhere else. When the accent color changes, one line changes.

### Editorial dashboard with keyboard support
Every action in the editor dashboard is reachable without a mouse: `Esc` closes modals, arrow keys navigate the tag picker, `Ctrl/Cmd + S` saves a post, `Enter` submits the active suggestion.

---

## What I learned building this

- Designing a permission model that scales cleanly from reader to editor is a design problem, not a code problem. The permission classes came after I had written the fourth `if user.role == ...` check and realised it was time.
- Cache invalidation is easier when the cached value is small. Caching a dict of IDs and rendering on the fly was simpler than caching fully serialized HTML.
- Vanilla JavaScript is not a compromise. For pages this size, a single module with a state object and a render function is easier to reason about than a component tree.
- The hard part of a blog is not the blog. It is the pipeline that decides what gets published and how it gets taken down.

---

## License

MIT.
