# MirrorMirror

## Table of Contents
---
- [MirrorMirror](#mirrormirror)
  - [Table of Contents](#table-of-contents)
  - [Deploying the Engine](#deploying-the-engine)
      - [A. Deploy on Azure from Scratch](#a-deploy-on-azure-from-scratch)
      - [B. Deploy on your own Server (Windows / Linux)](#b-deploy-on-your-own-server-windows--linux)
  - [API Documentation](#api-documentation)
        - [Authentication](#authentication)
        - [Account Management](#account-management)
        - [Profile/profile Management](#profileprofile-management)
        - [Friend Requests](#friend-requests)
        - [Meetings](#meetings)
        - [Notifications](#notifications)
        - [Posts](#posts)
        - [WebEx](#webex)
        - [AI \& Document Management (ChromaDB)](#ai--document-management-chromadb)
---
## Deploying the Engine
---
To deploy this engine for you own purposes:
1. first create a new repository using this repository as a template
2. Configure your python environment to be 3.13.7
3. Follow one of the following sections:
   - A. if you wish to deploy the engine on Azure from scratch
   - B. if you wish to host the engine on your own server
---
#### A. Deploy on Azure from Scratch
1. Create a Azure account
2. Obtain a subscription, note down its id as `your_subscription_id`
3. Create a resource under the subscription: `your_resource_name`
4. Create a azure webapp: `your_webapp_name`.
5. Go to your Azure Portal, search and select `Microsoft Entra ID`, then note down `your_tenant_id`
6. Go to your Azure Portal, create a new `App Registration`
   1. Search for and select `App Registration`
   2. Create a new Registration named `your_registration`(unused value for deployment)
   3. Note down the `Application (client) ID` as `your_client_id`
   4. Select Certificates & secrets.
   5. Select Client secrets, and then Select New client secret.
   6. Provide a description of the secret, and a duration.
   7. Select Add.
   8. Note down the value of the secret as `your_client_secret` 
7. Set your WebApp's environmental variables:
   1. Go to the Azure Portal and navigate to your Webapp
   2. In the left sidebar, go to `Settings` -> `Environment variables`.
   3. Add the following App settings:

 | Key                           | Value                      |
 | :---------------------------- | :------------------------- |
 | `PYTHON_ENABLE_OPENTELEMETRY` | `"false"`                  |
 | `FLASK_SECRET_KEY`            | `*a`                       |
 | `JWT_SECRET_KEY`              | `*b`                       |
 | `AZURE_CLIENT_ID`             | `your_client_id`           |
 | `AZURE_CLIENT_SECRET`         | `your_client_secret`       |
 | `AZURE_TENANT_ID`             | `your_tenant_id`           |
 | `WEBEX_CLIENT_ID`             | `NOTDONE`                  |
 | `WEBEX_ACCESS_TOKEN`          | `NOTDONE`                  |
 | `WEBEX_CLIENT_SECRET`         | `NOTDONE`                  |
 | `WEBEX_REDIRECT_URI`          | `"https://localhost:3000"` |

 `*x`: your own set secret key value.

8. On github web view of your repository, under `Settings Tab -> Secrets and Variables -> Actions`:
   
a. define the following `Repository Variables`:

| Key                     | Value                      |
| :---------------------- | :------------------------- |
| `RESOURCE_NAME`         | `your_resource_name`       |
| `WEBAPP_NAME`           | `your_webapp_name`         |
| `TENANT_ID`             | `your_tenant_id`           |
| `AZURE_SUBSCRIPTION_ID` | `your_subscription_id`     |
| `WEBAPP_CLIENT_ID`      | `your_client_id`           |
| `WEBEX_REDIRECT_URI`    | `"https://localhost:3000"` |

b. define the following `Repository Secrets`:
   
| Key                    | Value                |
| :--------------------- | :------------------- |
| `FLASK_SECRET_KEY`     | `*a`                 |
| `JWT_SECRET_KEY`       | `*b`                 |
| `WEBAPP_CLIENT_SECRET` | `your_client_secret` |
| `WEBEX_CLIENT_ID`      | `NOTDONE`            |
| `WEBEX_ACCESS_TOKEN`   | `NOTDONE`            |
| `WEBEX_CLIENT_SECRET`  | `NOTDONE`            |

`*x`: your own set secret key value.

1. Deploy your application by calling `Deploy Webapp` action via
   1. Arbitrary Pull Request
   2. Manually on Github Webview under `Actions` Tab
---
#### B. Deploy on your own Server (Windows / Linux)
1. Create a new repository from template.
2. If you are on Windows, ensure you have WSL2 (Ubuntu) installed. For native Linux, ensure your package manager is up to date via 
```bash
sudo apt update && sudo apt install python3-pip python3-venv nginx
```
1. Install Gunicorn via
```bash
pip install gunicorn
```
1. Set up environment Variables

| Key                   | Value                      |
| :-------------------- | :------------------------- |
| `FLASK_SECRET_KEY`    | `*`                        |
| `JWT_SECRET_KEY`      | `*`                        |
| `WEBEX_CLIENT_ID`     | `NOTDONE`                  |
| `WEBEX_ACCESS_TOKEN`  | `NOTDONE`                  |
| `WEBEX_CLIENT_SECRET` | `NOTDONE`                  |
| `WEBEX_REDIRECT_URI`  | `"https://localhost:3000"` |

1. Serve with Gunicorn
```bash
gunicorn --workers 1 --bind 0.0.0.0:8000 app:app
```
---
## API Documentation
---
The MirrorMirror engine provides a RESTful API for managing accounts, profiles/profiles, social features, meetings, WebEx integration, and semantic search. Most endpoints require a JWT token in the `Authorization: Bearer <token>` header.

##### Authentication

| Endpoint             | Method | Description                           | Parameters                                     |
| :------------------- | :----- | :------------------------------------ | :--------------------------------------------- |
| `/api/auth/register` | `POST` | Register a new account                | `email`, `password`, `organization` (optional) |
| `/api/auth/login`    | `POST` | Login and receive a JWT token         | `email`, `password`                            |
| `/api/auth/me`       | `GET`  | Get current authenticated user's info | None                                           |

##### Account Management

| Endpoint                | Method   | Description                                                |
| :---------------------- | :------- | :--------------------------------------------------------- |
| `/api/account`          | `GET`    | Get current account details with all profiles              |
| `/api/account`          | `PUT`    | Update account information (email, password, organization) |
| `/api/account`          | `DELETE` | Delete account and all associated profiles                 |
| `/api/account/profiles` | `GET`    | Get all profiles for the current account                   |
| `/api/account/stats`    | `GET`    | Get account statistics                                     |

##### Profile/profile Management

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

##### Friend Requests

| Endpoint               | Method | Description                        | Parameters  |
| :--------------------- | :----- | :--------------------------------- | :---------- |
| `/api/friends/request` | `POST` | Send a friend request to a profile | `profileId` |

##### Meetings

| Endpoint        | Method | Description                                | Parameters |
| :-------------- | :----- | :----------------------------------------- | :--------- |
| `/api/meetings` | `GET`  | Get upcoming meetings for the current user | None       |

##### Notifications

| Endpoint                       | Method   | Description                 | Parameters |
| :----------------------------- | :------- | :-------------------------- | :--------- |
| `/api/notifications/<id>/read` | `POST`   | Mark a notification as read | None       |
| `/api/notifications/<id>`      | `DELETE` | Delete a notification       | None       |

##### Posts

| Endpoint                 | Method | Description                   | Parameters                                                  |
| :----------------------- | :----- | :---------------------------- | :---------------------------------------------------------- |
| `/api/posts`             | `GET`  | Get all posts (auth optional) | None                                                        |
| `/api/posts`             | `POST` | Create a new post             | `content`, `imageUrl` (optional), `quotedPostId` (optional) |
| `/api/posts/<id>/like`   | `POST` | Like a post                   | None                                                        |
| `/api/posts/<id>/unlike` | `POST` | Unlike a post                 | None                                                        |

##### WebEx

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

##### AI & Document Management (ChromaDB)

| Endpoint                | Method   | Description                              |
| :---------------------- | :------- | :--------------------------------------- |
| `/api/documents/upload` | `POST`   | Upload and embed documents               |
| `/api/documents/query`  | `POST`   | Query for semantically similar documents |
| `/api/documents/delete` | `DELETE` | Delete documents by ID                   |
| `/api/documents/info`   | `GET`    | Get collection statistics                |
| `/api/documents/update` | `PUT`    | Update existing document embeddings      |
