# MirrorMirror

## API Documentation

The MirrorMirror engine provides a RESTful API for managing accounts, profiles/profiles, social features, meetings, WebEx integration, and semantic search. Most endpoints require a JWT token in the `Authorization: Bearer <token>` header.

### Authentication

| Endpoint             | Method | Description                           | Parameters                                     |
| :------------------- | :----- | :------------------------------------ | :--------------------------------------------- |
| `/api/auth/register` | `POST` | Register a new account                | `email`, `password`, `organization` (optional) |
| `/api/auth/login`    | `POST` | Login and receive a JWT token         | `email`, `password`                            |
| `/api/auth/me`       | `GET`  | Get current authenticated user's info | None                                           |

### Account Management

| Endpoint                | Method   | Description                                                |
| :---------------------- | :------- | :--------------------------------------------------------- |
| `/api/account`          | `GET`    | Get current account details with all profiles              |
| `/api/account`          | `PUT`    | Update account information (email, password, organization) |
| `/api/account`          | `DELETE` | Delete account and all associated profiles                 |
| `/api/account/profiles` | `GET`    | Get all profiles for the current account                   |
| `/api/account/stats`    | `GET`    | Get account statistics                                     |

### Profile/profile Management

| Endpoint                        | Method   | Description                               | Parameters                                                                             |
| :------------------------------ | :------- | :---------------------------------------- | :------------------------------------------------------------------------------------- |
| `/api/profiles`                 | `POST`   | Create a new profile profile              | `name`, `location`, `latitude`, `longitude`, `class_size`, `availability`, `interests` |
| `/api/profiles`                 | `GET`    | List profiles (newest first)              | `limit` (optional)                                                                     |
| `/api/profiles/<id>`            | `GET`    | Get profile profile details and friends   | None                                                                                   |
| `/api/profiles/<id>`            | `PUT`    | Update profile profile                    | Any profile field                                                                      |
| `/api/profiles/<id>`            | `DELETE` | Delete profile profile                    | None                                                                                   |
| `/api/profiles/search`          | `POST`   | Semantic search for profiles by interests | `interests` (list/string), `n_results` (optional)                                      |
| `/api/profiles/<id>/connect`    | `POST`   | Connect two profiles                      | `from_profile_id`                                                                      |
| `/api/profiles/<id>/friends`    | `GET`    | Get friends for a profile                 | None                                                                                   |
| `/api/profiles/<id>/disconnect` | `DELETE` | Remove friendship                         | `from_profile_id`                                                                      |

### Friend Requests

| Endpoint               | Method | Description                        | Parameters  |
| :--------------------- | :----- | :--------------------------------- | :---------- |
| `/api/friends/request` | `POST` | Send a friend request to a profile | `profileId` |

### Meetings

| Endpoint        | Method | Description                                | Parameters |
| :-------------- | :----- | :----------------------------------------- | :--------- |
| `/api/meetings` | `GET`  | Get upcoming meetings for the current user | None       |

### Notifications

| Endpoint                       | Method   | Description                 | Parameters |
| :----------------------------- | :------- | :-------------------------- | :--------- |
| `/api/notifications/<id>/read` | `POST`   | Mark a notification as read | None       |
| `/api/notifications/<id>`      | `DELETE` | Delete a notification       | None       |

### Posts

| Endpoint                 | Method | Description                   | Parameters                                                  |
| :----------------------- | :----- | :---------------------------- | :---------------------------------------------------------- |
| `/api/posts`             | `GET`  | Get all posts (auth optional) | None                                                        |
| `/api/posts`             | `POST` | Create a new post             | `content`, `imageUrl` (optional), `quotedPostId` (optional) |
| `/api/posts/<id>/like`   | `POST` | Like a post                   | None                                                        |
| `/api/posts/<id>/unlike` | `POST` | Unlike a post                 | None                                                        |

### WebEx

| Endpoint                              | Method   | Description                       | Parameters                                                                       |
| :------------------------------------ | :------- | :-------------------------------- | :------------------------------------------------------------------------------- |
| `/api/webex/auth-url`                 | `GET`    | Get WebEx OAuth authorization URL | None                                                                             |
| `/api/webex/connect`                  | `POST`   | Connect WebEx account             | `code`                                                                           |
| `/api/webex/status`                   | `GET`    | Check WebEx connection status     | None                                                                             |
| `/api/webex/disconnect`               | `POST`   | Disconnect WebEx account          | None                                                                             |
| `/api/webex/meeting`                  | `POST`   | Create a WebEx meeting invitation | `title` (optional), `start_time` (optional), `end_time` (optional), `profile_id` |
| `/api/webex/meeting/<id>`             | `GET`    | Get meeting details               | None                                                                             |
| `/api/webex/meeting/<id>`             | `PUT`    | Update meeting times              | `start_time` (optional), `end_time` (optional)                                   |
| `/api/webex/meeting/<id>`             | `DELETE` | Delete a meeting                  | None                                                                             |
| `/api/webex/invitations`              | `GET`    | Get received invitations          | None                                                                             |
| `/api/webex/invitations/sent`         | `GET`    | Get sent invitations              | None                                                                             |
| `/api/webex/invitations/<id>/accept`  | `POST`   | Accept an invitation              | None                                                                             |
| `/api/webex/invitations/<id>/decline` | `POST`   | Decline an invitation             | None                                                                             |
| `/api/webex/invitations/<id>/cancel`  | `POST`   | Cancel a sent invitation          | None                                                                             |

### AI & Document Management (ChromaDB)

| Endpoint                | Method   | Description                              |
| :---------------------- | :------- | :--------------------------------------- |
| `/api/documents/upload` | `POST`   | Upload and embed documents               |
| `/api/documents/query`  | `POST`   | Query for semantically similar documents |
| `/api/documents/delete` | `DELETE` | Delete documents by ID                   |
| `/api/documents/info`   | `GET`    | Get collection statistics                |
| `/api/documents/update` | `PUT`    | Update existing document embeddings      |
