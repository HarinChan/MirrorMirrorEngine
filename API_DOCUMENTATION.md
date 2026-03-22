# MirrorMirrorEngine API Documentation

Last updated: 2026-03-22

## 1. Overview

This document describes all API endpoints currently implemented in the Flask backend.

- Base URL: provided by deployment environment
- Primary API namespace: `/api/*`
- Additional admin HTML routes: `/admin/*`
- Auth technology: JWT (Flask-JWT-Extended)

## 2. Global Conventions

### 2.1 Authentication and Authorization

- JWT is returned by `POST /api/auth/login`.
- Most protected endpoints require `Authorization: Bearer <token>`.
- JWT identity is typically the account ID.
- Admin routes require an admin role claim and `require_admin_dashboard_enabled` guard.

### 2.2 Content Types

- Most endpoints use `application/json`.
- Upload endpoints use `multipart/form-data`.
- Attachment retrieval can return binary content.

### 2.3 Common Response Patterns

Two response styles exist in code:

- Style A: `{"msg": "..."}` and optional `{"error": "..."}`
- Style B (AI/document APIs): `{"status": "success|error", "message": "..."}`

### 2.4 Error Status Usage

Common statuses seen across handlers:

- `400` validation or malformed input
- `401` authentication failure
- `403` authorization failure
- `404` resource not found
- `409` conflict/business rule violation
- `413` payload too large (upload)
- `500` internal/server integration errors
- `503` degraded or unavailable service

### 2.5 Pagination and Limits

- Messaging uses `page` and `per_page` (`per_page` max 100)
- Profile/classroom list supports `limit` (default 50, max 100)
- Search/document APIs support `n_results` with caps

## 3. Endpoint Inventory

## 3.1 Authentication and System

### POST /api/auth/register

- Auth: Public
- Purpose: Register account
- Body:
  - `email` (string, required)
  - `password` (string, required)
  - `organization` (string, optional)
- Success:
  - `201` -> `{"msg": "Account created successfully", "account_id": <int>}`
- Errors:
  - `400` invalid or missing fields
  - `409` account already exists
- Side effects: Creates account record

### POST /api/auth/login

- Auth: Public
- Purpose: Authenticate and return JWT
- Body:
  - `email` (string, required)
  - `password` (string, required)
- Success:
  - `200` -> `{"access_token": "...", "account_id": ...}`
- Errors:
  - `400` missing fields
  - `401` invalid credentials
- Side effects: None

### GET /api/auth/me

- Auth: JWT required
- Purpose: Return current account context (account, classrooms, friends, notifications)
- Success:
  - `200` -> nested account/context object
- Errors:
  - `404` account not found
- Side effects: None

### GET /api/health

- Auth: Public
- Purpose: Service health summary
- Success:
  - `200` or `503` -> `{"status": "healthy|degraded|unhealthy", "details": {...}}`
- Side effects: Executes health checks

### GET /api/latency-history

- Auth: JWT + admin role + dashboard enabled
- Purpose: Retrieve latency history data
- Success:
  - `200` latency history payload
- Errors:
  - `402` no data available yet
  - `403` not authorized

### GET /auth/admin

- Auth: JWT + admin role + dashboard enabled
- Purpose: Verify admin authentication
- Success:
  - `200` -> `{"msg": "Admin authenticated successfully"}`
- Errors:
  - `403` not admin

### GET /api/config

- Auth: JWT + admin role + dashboard enabled
- Purpose: Get safe runtime configuration values
- Success:
  - `200` safe config payload
- Errors:
  - `403` not authorized

### POST /api/config

- Auth: JWT + admin role + dashboard enabled
- Purpose: Update whitelisted runtime config key
- Body:
  - `key` (string, required)
  - `value` (string, required)
  - `ignoreAzure` (bool, optional)
  - `ignoreSqlcipher` (bool, optional)
- Success:
  - `200` -> `{"msg": "Configuration updated successfully"}`
- Errors:
  - `400` key not allowed
  - `403` not authorized
- Side effects: Updates config and refreshes services

## 3.2 Account APIs

### GET /api/account

- Auth: JWT required
- Purpose: Get account details and classrooms
- Success:
  - `200` -> `{"account": {...}, "classrooms": [...]}`
- Errors:
  - `404` account not found

### PUT /api/account

- Auth: JWT required
- Purpose: Update account fields
- Body (optional fields):
  - `email` (string)
  - `organization` (string)
  - `password` (string)
- Success:
  - `200` -> updated account payload
- Errors:
  - `400` validation errors
  - `409` email conflict
- Side effects: Updates account; may re-hash password

### DELETE /api/account

- Auth: JWT required
- Purpose: Delete account and associated resources
- Success:
  - `200` -> `{"msg": "Account deleted successfully", "deleted_classrooms": <int>}`
- Errors:
  - `404` account not found
- Side effects: Hard delete with cascade behavior

### GET /api/account/profiles

- Auth: JWT required
- Purpose: List account classrooms/profiles
- Success:
  - `200` -> classroom list with counts
- Errors:
  - `404` account not found

### GET /api/account/stats

- Auth: JWT required
- Purpose: Aggregate account statistics
- Success:
  - `200` stats payload
- Errors:
  - `404` account not found

## 3.3 Profiles/Classrooms APIs

Note: These endpoints are exposed with dual aliases where shown.

### POST /api/profiles

### POST /api/classrooms

- Auth: JWT required
- Purpose: Create profile/classroom
- Body:
  - `name` (string, required)
  - `description` (string, optional)
  - `location` (string, optional)
  - `latitude` (number, optional)
  - `longitude` (number, optional)
  - `class_size` (int, optional)
  - `availability` (array of `{day,time}`, optional)
  - `interests` (array[string], optional)
- Success:
  - `201` created payload
- Errors:
  - `400` validation errors
  - `404` account not found
- Side effects: Creates profile and writes searchable interest docs

### GET /api/profiles/<int:profile_id>

### GET /api/classrooms/<int:profile_id>

- Auth: JWT required
- Purpose: Read profile/classroom details
- Success:
  - `200` profile payload
- Errors:
  - `404` profile not found

### PUT /api/profiles/<int:profile_id>

### PUT /api/classrooms/<int:profile_id>

- Auth: JWT + ownership required
- Purpose: Update profile/classroom
- Body: same shape as create (partial)
- Success:
  - `200` updated payload
- Errors:
  - `400` validation
  - `403` forbidden (not owner)
  - `404` not found
- Side effects: Updates search index when interests change

### DELETE /api/profiles/<int:profile_id>

### DELETE /api/classrooms/<int:profile_id>

- Auth: JWT + ownership required
- Purpose: Delete profile/classroom
- Success:
  - `200` delete summary
- Errors:
  - `403` forbidden
  - `404` not found
- Side effects: Removes profile and related relations/index data

### POST /api/profiles/search

### POST /api/classrooms/search

- Auth: JWT required
- Purpose: Semantic search by interests
- Body:
  - `interests` (string or array[string], required)
  - `n_results` (int, optional)
- Success:
  - `200` matched profiles with similarity metrics
- Errors:
  - `400` invalid input
  - `500` search failure

### POST /api/profiles/<int:profile_id>/connect

### POST /api/classrooms/<int:profile_id>/connect

- Auth: JWT required
- Purpose: Connect two profiles as friends
- Body:
  - `from_profile_id` (int, required)
- Success:
  - `201` connection details
- Errors:
  - `400` invalid or duplicate relationship
  - `403` not allowed
  - `404` profiles not found
- Side effects: Creates bidirectional accepted relations

### GET /api/profiles/<int:profile_id>/friends

### GET /api/classrooms/<int:profile_id>/friends

- Auth: JWT required
- Purpose: List friends for profile
- Success:
  - `200` friend list and count
- Errors:
  - `404` profile not found

### DELETE /api/profiles/<int:profile_id>/disconnect

### DELETE /api/classrooms/<int:profile_id>/disconnect

- Auth: JWT required
- Purpose: Remove friendship
- Body:
  - `from_profile_id` (int, required)
- Success:
  - `200` disconnect confirmation
- Errors:
  - `403` forbidden
  - `404` relation not found
- Side effects: Deletes both relation directions

### GET /api/profiles

### GET /api/classrooms

- Auth: JWT required
- Purpose: List classrooms/profiles
- Query:
  - `limit` (int, optional)
- Success:
  - `200` list payload

## 3.4 Friends APIs

### POST /api/friends/request

- Auth: JWT required
- Purpose: Send friend request
- Body:
  - `profileId` or `classroomId` (int, required)
- Success:
  - `201` pending request created
  - `200` auto-accept when reciprocal pending exists
- Errors:
  - `400` self request, duplicate request, already friends
  - `404` target/account/profile missing
- Side effects: Creates friend request, possible relation updates, notification creation

### POST /api/friends/accept

- Auth: JWT required
- Purpose: Accept pending friend request
- Body:
  - `requestId` or `senderId` (one required)
- Success:
  - `200` accepted
- Errors:
  - `403` not recipient
  - `404` request not found
- Side effects: Updates request status, creates/updates relation, sends notification

### POST /api/friends/reject

- Auth: JWT required
- Purpose: Reject pending friend request
- Body:
  - `requestId` or `senderId` (one required)
- Success:
  - `200` rejected
- Errors:
  - `403` not recipient
  - `404` request not found
- Side effects: Updates request status

### DELETE /api/friends/<int:friend_id>

- Auth: JWT required
- Purpose: Remove friendship
- Success:
  - `200` removed
- Errors:
  - `404` relation not found
- Side effects: Deletes friend relations

## 3.4.1 Chat and AI APIs

### POST /api/chat

- Auth: Public
- Purpose: RAG-style chat response generation
- Body:
  - `message` (string, required)
  - `history` (array, optional)
  - `n_results` (int, optional)
- Success:
  - `200` -> `{"status": "success", "reply": "...", "context": [...]}`
- Errors:
  - `400` invalid/missing message or bad history format
  - `500` inference or retrieval service errors
- Side effects: Reads semantic index; no persistent write in normal path

### POST /api/chat/transcribe

- Auth: Public
- Purpose: Transcribe uploaded audio
- Content type: `multipart/form-data`
- Form:
  - `audio` or `file` or `recording` (file, required)
  - `hotwords` (string, optional)
- Success:
  - `200` -> `{"status": "success", "transcript": "...", "engine": "faster-whisper"}`
- Errors:
  - `400` missing audio
  - `500` transcription engine unavailable/error
- Side effects: Temporary audio processing only

## 3.5 Messaging APIs

### GET /api/conversations

- Auth: JWT required
- Purpose: List user conversations
- Success:
  - `200` conversation list with unread counters
- Errors:
  - `404` account/profile not found

### GET /api/conversations/<int:conversation_id>/messages

- Auth: JWT + membership required
- Purpose: Paginated message retrieval
- Query:
  - `page` (int, optional)
  - `per_page` (int, optional, max 100)
- Success:
  - `200` messages + pagination metadata
- Errors:
  - `403` not participant
  - `404` conversation not found

### POST /api/conversations/<int:conversation_id>/messages

- Auth: JWT + membership required
- Purpose: Send message
- Body:
  - `content` (string, optional if attachment present)
  - `messageType` (string, optional; text/image/file/system)
  - `attachmentUrl` (string, optional)
- Success:
  - `201` created message
- Errors:
  - `400` invalid content/type
  - `403` not participant
  - `404` conversation not found
- Side effects: Creates message and updates conversation activity

### POST /api/messages/<int:message_id>/read

- Auth: JWT required
- Purpose: Mark single message as read
- Success:
  - `200`
- Errors:
  - `400` own message cannot be marked read
  - `403` not participant
  - `404` message not found
- Side effects: Creates read receipt record

### POST /api/conversations/<int:conversation_id>/mark-all-read

- Auth: JWT + membership required
- Purpose: Mark all unread messages as read
- Success:
  - `200` with count
- Errors:
  - `403` not participant
  - `404` conversation not found
- Side effects: Bulk read receipt creation

### POST /api/conversations/start

- Auth: JWT required
- Purpose: Start direct conversation with friend
- Body:
  - `friendId` (int, required)
- Success:
  - `200` existing conversation returned
  - `201` new conversation created
- Errors:
  - `403` only friends can be messaged
  - `404` friend/account/profile not found
- Side effects: Creates direct conversation when needed

### PUT /api/messages/<int:message_id>

- Auth: JWT + sender required
- Purpose: Edit message
- Body:
  - `content` (string, required)
- Success:
  - `200` updated
- Errors:
  - `400` empty or invalid
  - `403` not sender
  - `404` not found
- Side effects: Sets edited timestamp

### DELETE /api/messages/<int:message_id>

- Auth: JWT + sender required
- Purpose: Soft-delete message
- Success:
  - `200`
- Errors:
  - `403` not sender
  - `404` not found
- Side effects: Marks deleted and replaces message content

### POST /api/messages/<int:message_id>/reactions

- Auth: JWT + membership required
- Purpose: Toggle emoji reaction
- Body:
  - `emoji` (string, required)
- Success:
  - `201` added
  - `200` removed (toggle off)
- Errors:
  - `403` not participant
  - `404` message not found
- Side effects: Adds/removes reaction rows

### GET /api/messages/<int:message_id>/reactions

- Auth: JWT + membership required
- Purpose: Get grouped reactions
- Success:
  - `200` grouped reaction counts and users
- Errors:
  - `403` not participant
  - `404` message not found

## 3.6 Notifications APIs

### GET /api/notifications

- Auth: JWT required
- Purpose: List notifications for current user
- Success:
  - `200` notifications sorted newest first
- Errors:
  - `404` account not found

### POST /api/notifications/<int:notification_id>/read

- Auth: JWT + ownership required
- Purpose: Mark notification as read
- Success:
  - `200`
- Errors:
  - `404` not found
- Side effects: Updates read flag

### DELETE /api/notifications/<int:notification_id>

- Auth: JWT + ownership required
- Purpose: Delete notification
- Success:
  - `200`
- Errors:
  - `404` not found
- Side effects: Hard delete

## 3.7 Posts and Attachments APIs

### POST /api/posts/attachments/upload

- Auth: JWT required
- Purpose: Upload post attachment
- Content type: `multipart/form-data`
- Form:
  - `file` or `attachment` (file, required)
- Validation:
  - Allowed MIME types include common image/PDF/Office formats
  - Max file size: 20MB
- Success:
  - `201` attachment metadata including `storageKey` and `url`
- Errors:
  - `400` invalid upload
  - `404` account not found
  - `413` too large
- Side effects: Writes file to storage folder

### GET /api/posts/attachments/<path:storage_key>

- Auth: Public
- Purpose: Serve attachment file
- Success:
  - `200` binary response
- Errors:
  - `404` file not found

### GET /api/posts

- Auth: Optional JWT
- Purpose: List posts timeline
- Success:
  - `200` posts array with author, attachments, likes, comments, `isLiked`

### POST /api/posts

- Auth: JWT required
- Purpose: Create post
- Body:
  - `content` (string, required)
  - `classroomId` (int, optional fallback to first profile)
  - `quotedPostId` (int, optional)
  - `attachments` (array, optional)
- Success:
  - `201` created post
- Errors:
  - `400` invalid payload/no content
  - `404` account/classroom not found
- Side effects: Creates post and attachments, writes to semantic index

### POST /api/posts/<int:post_id>/like

- Auth: JWT required
- Purpose: Like post
- Success:
  - `200` updated like count
- Errors:
  - `404` post/account not found
- Side effects: Adds like relation

### POST /api/posts/<int:post_id>/unlike

- Auth: JWT required
- Purpose: Unlike post
- Success:
  - `200` updated like count
- Errors:
  - `404` post/account not found
- Side effects: Removes like relation

### DELETE /api/posts/<int:post_id>

- Auth: JWT + ownership required
- Purpose: Delete post
- Success:
  - `200`
- Errors:
  - `403` forbidden
  - `404` not found
- Side effects: Deletes post and associated index/files

## 3.8 Meetings APIs

### GET /api/meetings

- Auth: JWT required
- Purpose: List upcoming meetings user created/participates in
- Success:
  - `200` meetings list
- Errors:
  - `404` account/profile not found

### GET /api/meetings/public

- Auth: JWT required
- Purpose: List public meetings
- Success:
  - `200` meetings list

### GET /api/meetings/public/trending

- Auth: JWT required
- Purpose: Public meetings ranked by trend score
- Success:
  - `200` capped trending list

### POST /api/meetings/<int:meeting_id>/join

- Auth: JWT required
- Purpose: Join a public meeting
- Success:
  - `200`
- Errors:
  - `403` not public or not joinable
  - `404` meeting not found
  - `409` full/cancelled
- Side effects: Adds participant and may trigger WebEx creation

## 3.9 WebEx APIs

### GET /api/webex/auth-url

- Auth: JWT required
- Purpose: Get OAuth URL for WebEx connect flow
- Success:
  - `200` -> `{"url": "..."}`

### POST /api/webex/connect

- Auth: JWT required
- Purpose: Exchange OAuth code and store WebEx tokens
- Body:
  - `code` (string, required)
- Success:
  - `200` connected
- Errors:
  - `400` missing code
  - `404` account not found
- Side effects: Stores tokens and expiry on account

### GET /api/webex/status

- Auth: JWT required
- Purpose: Check whether account is WebEx-connected
- Success:
  - `200` -> `{"connected": <bool>}`
- Errors:
  - `404` account not found

### POST /api/webex/disconnect

- Auth: JWT required
- Purpose: Remove WebEx credentials
- Success:
  - `200`
- Errors:
  - `404` account not found
- Side effects: Clears stored WebEx tokens

### POST /api/webex/meeting

- Auth: JWT required
- Purpose: Create meeting and optional invitations
- Body:
  - `title` (string, optional)
  - `description` (string, optional)
  - `start_time` (ISO datetime, optional)
  - `end_time` (ISO datetime, optional)
  - `is_public` (bool, optional)
  - `max_participants` (int, optional)
  - `classroom_ids` or `classroom_id` (required for private invitations)
- Success:
  - `201` meeting + invitation details
- Errors:
  - `400` validation failures
  - `404` classroom not found
- Side effects: Creates meeting/invitations and updates vector index

### GET /api/webex/meeting/<int:meeting_id>

- Auth: JWT + visibility/participant/owner checks
- Purpose: Get meeting details
- Success:
  - `200`
- Errors:
  - `403` unauthorized view
  - `404` not found

### DELETE /api/webex/meeting/<int:meeting_id>

- Auth: JWT + creator required
- Purpose: Cancel meeting
- Success:
  - `200`
- Errors:
  - `403` unauthorized / missing WebEx connection
  - `404` not found
- Side effects: Marks meeting cancelled; cancels pending invitations

### PUT /api/webex/meeting/<int:meeting_id>

- Auth: JWT + creator required
- Purpose: Update meeting
- Body: partial update fields such as title/time/description/visibility/max participants
- Success:
  - `200`
- Errors:
  - `400` invalid update
  - `403` unauthorized
  - `404` not found
- Side effects: Updates DB and external sync paths

### GET /api/webex/invitations

- Auth: JWT required
- Purpose: List received pending invitations
- Success:
  - `200` invitation list
- Errors:
  - `404` account/profile not found

### GET /api/webex/invitations/sent

- Auth: JWT required
- Purpose: List sent pending invitations
- Success:
  - `200` invitation list
- Errors:
  - `404` account/profile not found

### POST /api/webex/invitations/<int:invitation_id>/accept

- Auth: JWT + invitation recipient required
- Purpose: Accept invitation
- Success:
  - `201` accepted and meeting payload
- Errors:
  - `403` unauthorized
  - `404` invitation missing
  - `409` meeting full/already accepted
- Side effects: Updates invitation and participant membership

### POST /api/webex/invitations/<int:invitation_id>/decline

- Auth: JWT + invitation recipient required
- Purpose: Decline invitation
- Success:
  - `200`
- Errors:
  - `404` invitation missing
- Side effects: Marks invitation declined

### POST /api/webex/invitations/<int:invitation_id>/cancel

- Auth: JWT + invitation sender required
- Purpose: Cancel sent invitation
- Success:
  - `200`
- Errors:
  - `404` invitation missing
- Side effects: Marks invitation cancelled

### POST /api/webex/meeting/<int:meeting_id>/invitees

- Auth: JWT + creator required
- Purpose: Add invitees to existing meeting
- Body:
  - `classroom_ids` (array[int], required)
- Success:
  - `201` invitation summary with skipped entries
- Errors:
  - `403` not creator
- Side effects: Creates invitation rows

## 3.10 ChromaDB/Document APIs

### POST /api/documents/upload

- Auth: Public
- Purpose: Store documents in vector DB
- Body:
  - `documents` (array[string], required)
  - `metadatas` (array[object], optional)
  - `ids` (array[string], optional)
- Success:
  - `200` or `201` success payload
- Errors:
  - `400` invalid document input
  - `500` vector service errors
- Side effects: Inserts vectors/documents

### POST /api/documents/query

- Auth: Public
- Purpose: Semantic document retrieval
- Body:
  - `query` (string, required)
  - `n_results` (int, optional)
  - `where` (object, optional)
  - `min_similarity` (number, optional)
- Success:
  - `200` query results
- Errors:
  - `400` invalid query
  - `500` service errors

### DELETE /api/documents/delete

- Auth: Public
- Purpose: Delete documents by IDs
- Body:
  - `ids` (array[string], required)
- Success:
  - `200`
- Errors:
  - `400` invalid IDs
  - `500` service errors
- Side effects: Removes vectors/documents

### GET /api/documents/info

- Auth: Public
- Purpose: Return collection metadata
- Success:
  - `200`
- Errors:
  - `500` service errors

### PUT /api/documents/update

- Auth: Public
- Purpose: Update one indexed document
- Body:
  - `id` (string, required)
  - `document` (string, required)
  - `metadata` (object, optional)
- Success:
  - `200`
- Errors:
  - `400` invalid payload
  - `500` service errors
- Side effects: Updates document/vector entry

## 3.11 Admin Setup and Dashboard Routes

### GET /admin/initial-setup

- Auth: Guarded by dashboard enabled check
- Purpose: Render initial setup page
- Response: HTML

### POST /admin/initial-setup

- Auth: Guarded by dashboard enabled check
- Purpose: Submit initial setup configuration
- Body/form includes:
  - `initial_setup_key` (required)
  - required/suggested config values
  - `ADMIN_ACCOUNTS` JSON
- Success:
  - `200` setup completed message
- Errors:
  - `400` invalid setup key or missing required config
- Side effects: Persists setup config, creates admin account, refreshes services

### POST /api/initial-setup/reset

- Auth: JWT + admin role + dashboard enabled
- Purpose: Factory reset configuration
- Body:
  - `initial_setup_key` (required)
- Success:
  - `200`
- Errors:
  - `400` invalid key
- Side effects: Resets local config and service state

### GET /api/initial-setup/status

- Auth: Public
- Purpose: Setup completion status
- Success:
  - `200` with `setup_completed` and key requirements

### GET /admin/login

- Auth: Guarded by dashboard enabled check
- Purpose: Render admin login page
- Response: HTML

### GET /admin/dashboard

- Auth: Guarded by dashboard enabled check
- Purpose: Render admin dashboard page
- Response: HTML

### GET /api/config/admin-accounts

- Auth: JWT + admin role + dashboard enabled
- Purpose: List admin account emails
- Success:
  - `200`
- Errors:
  - `403`

### POST /api/config/admin-accounts

- Auth: JWT + admin role + dashboard enabled
- Purpose: Add admin account
- Body:
  - `email` (string, required)
  - `password` (string, required)
- Success:
  - `201`
- Errors:
  - `400` missing fields
  - `409` already exists
- Side effects: Hashes and stores admin credentials in config

### DELETE /api/config/admin-accounts

- Auth: JWT + admin role + dashboard enabled
- Purpose: Delete admin account
- Body:
  - `email` (string, required)
- Success:
  - `200`
- Errors:
  - `400` missing email
  - `404` not found
- Side effects: Removes admin entry from config

## 4. Known Inconsistencies and Notes

- Profile/classroom naming is mixed (`profiles` vs `classrooms`) with route aliases.
- Error envelope format varies between classic API modules and AI/document modules.
- Password hashing paths differ across registration/login/update flows.
- Relationship modeling combines friend requests and bidirectional relations.
- Some routes use first profile heuristics where a user has multiple profiles.

## 5. Quick Security/Operations Checklist

- Enforce auth on currently public document APIs if those should not be public.
- Standardize response envelope and error schema for easier client integration.
- Unify password hashing strategy across all account mutation endpoints.
- Consider consistent model naming for profile/classroom in API payloads.
- Add OpenAPI generation or schema tests to detect endpoint contract drift.
