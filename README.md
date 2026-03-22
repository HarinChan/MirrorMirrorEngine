# MirrorMirror

MirrorMirror engine is the social networking engine for PenPals AI

## Project Structure

```
.
├── .github/                   #github actions and PR template  
├── asset/                     #miscellaneous HTML
├── models/                    #default language model location
├── src/                            
│   └── app/
│       ├── blueprint/         #REST routes
│       ├── model/             #database models
│       ├── service/           #service classes
│       ├── templates/         #admin dashboard HTML
│       ├── config.py          #configuration loader
│       ├── helper.py          #helper functions
│       ├── init_db.py         #dummy data
│       └── main.py
│   └── test/                  #pytest files
├── .gitignore
├── app.py                     #entry point (wraps src/app/main.py)
├── LICENSE                    #MIT License
├── pytest.ini                 #pytest configuration
└── README.md                  #this file :)
```

## Building from source (.exe)
---
To build the engine from source on Windows follow the instructions below. Please note that you will need a valid `webex_client_id`and `webex_client_secret`. Go to **Retrieving Webex Tokens** for instructions on how to create a Webex integration on the developer portal.

Prerequisites: Ensure that you have installed Python (>= 3.12) and pip. We highly recommend running a virtual environment to ensure only required packages are compiled.
```
python -m venv .venv
\.venv\Scripts\activate
```

1. Install all required dependencies
```
pip install -r requirements
pip install nuitka
```

2. Download the recommended language model
```
cd \models\
python download.py
cd ..
```
If you wish to use a different model, go to section **Bring your own Model**
If you wish to include demo accounts follow **Inserting dummy data**

3. Create a `.env`file and add the following:
```
WEBEX_CLIENT_ID = 'your_webex_client_id'
WEBEX_CLIENT_SECRET = 'your_webex_client_secret'
WEBEX_REDIRECT_URI = 'http://localhost:3000'
```

4. Run the compile script
```
\build-with-openvino.ps1
```
Note: This step may take several hours, especially when running for the first time and on low-end hardware, since the whole OpenVino GenAI package will be compiled. 

The final build can be found in `\build\app.dist`with the main executable `mirrormirror-engine.exe`

## Running MirrorMirror (Deployment)
---
To deploy MirrorMirror you have two options:
- A. Run a packaged build
- B. Run directly with Python

**A. Running a packaged build**
1. Run the executable (either in Terminal or by double click)
```
mirrormirror-engine.exe
```

**B. Running directly with Python**
1. Install all requirements
```
pip install -r requirements
```

2. Ensure you have a valid `.env`file configured as follows:
```
WEBEX_CLIENT_ID = 'your_webex_client_id'
WEBEX_CLIENT_SECRET = 'your_webex_client_secret'
WEBEX_REDIRECT_URI = 'http://localhost:3000'
```

2. Run the application
```
python app.py
```

**Port Configuration**
MirrorMirror will automatically find the next open port between `5000`and `6000`. To make your instance publicly available you will need to forward that port.

## Retrieving Webex Tokens
---
1. Signup / Log into the Webex developer portal at [Webex for Developers](https://developer.webex.com/)
2. Click Profile -> My Webex Apps -> Create a new App -> Integration
3. add the following redirect URIs: `http://localhost:3000`, `https://localhost:3000`
4. make sure to give the following permissions: `meeting:participants_write`, `meeting:participants_read`, `meeting:schedules_write`, `meeting:schedules_read`
5. Copy Client ID and Client Secret

## Inserting dummy data
---
If you wish to start with some example profiles and data run before:
```
python -m src.app.init_db
```
(if you are building from source do this before compilation)
## Bring your own Model
---
If you wish to use a different language model, add the following line in the `.env`file before building or running MirrorMirror:
```
OPENVINO_MODEL_DIR = 'your_path'
```
If using an absolute path, there is no further action needed. If using a relative path, make sure to copy the model to the right location relative to `\build\app.dist\mirrormirror-engine.exe`

## Notes on NPU usage
---
If you wish to use an Intel NPU, make sure your model is compatible. A list of pre-compiled supported models can be found here:
We recommended running from Python directly for maximum compatibility in this case.

## Experimental Features
---
The following are experimental features, which may include some untested functions and behaviour.
### Deploy on Azure
1. Create a Azure account
2. Obtain a subscription, note down its id as `your_subscription_id`
3. Create a resource under the subscription: `your_resource_name`
4. Create a azure webapp: `your_webapp_name`.
5. Go to your Azure Portal, search and select `Microsoft Entra ID`, then note down `your_tenant_id`
6. Go to your Azure Portal, create a new `App Registration`
   7. Search for and select `App Registration`
   8. Create a new Registration named `your_registration`(unused value for deployment)
   9. Note down the `Application (client) ID` as `your_client_id`
   10. Select Certificates & secrets.
   11. Select Client secrets, and then Select New client secret.
   12. Provide a description of the secret, and a duration.
   13. Select Add.
   14. Note down the value of the secret as `your_client_secret` 
15. Set your WebApp's environmental variables:
   16. Go to the Azure Portal and navigate to your Webapp
   17. In the left sidebar, go to `Settings` -> `Environment variables`.
   18. Add the following App settings:

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

19. On github web view of your repository, under `Settings Tab -> Secrets and Variables -> Actions`:
   
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
   2. Arbitrary Pull Request
   3. Manually on Github Webview under `Actions` Tab

### Admin Dashboard
To enable the Admin Dashboard add this to `.env`:
```
ADMIN_DASHBOARD_ENABLED=true
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
