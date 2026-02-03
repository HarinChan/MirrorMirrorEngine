# MirrorMirror

## API Documentation

The MirrorMirror engine provides a RESTful API for managing accounts, classrooms, and semantic search. Most endpoints require a JWT token in the `Authorization: Bearer <token>` header.

### Authentication

| Endpoint | Method | Description | Parameters |
| :--- | :--- | :--- | :--- |
| `/api/auth/register` | `POST` | Register a new account | `email`, `password`, `organization` (optional) |
| `/api/auth/login` | `POST` | Login and receive a JWT token | `email`, `password` |
| `/api/auth/me` | `GET` | Get current authenticated user's info | None |

### Account Management

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/account` | `GET` | Get current account details with all classrooms |
| `/api/account` | `PUT` | Update account information (email, password, organization) |
| `/api/account` | `DELETE` | Delete account and all associated classrooms |
| `/api/account/classrooms` | `GET` | Get all classrooms for the current account |
| `/api/account/stats` | `GET` | Get account statistics |

### Classroom Management

| Endpoint | Method | Description | Parameters |
| :--- | :--- | :--- | :--- |
| `/api/classrooms` | `POST` | Create a new classroom | `name`, `location`, `latitude`, `longitude`, `class_size`, `availability`, `interests` |
| `/api/classrooms/<id>` | `GET` | Get classroom details and friends | None |
| `/api/classrooms/<id>` | `PUT` | Update classroom information | Any classroom field |
| `/api/classrooms/<id>` | `DELETE` | Delete classroom | None |
| `/api/classrooms/search` | `POST` | Semantic search for classrooms | `interests` (list/string), `n_results` (optional) |
| `/api/classrooms/<id>/connect` | `POST` | Connect with another classroom | `from_classroom_id` |
| `/api/classrooms/<id>/friends` | `GET` | Get all friends for a classroom | None |
| `/api/classrooms/<id>/disconnect` | `DELETE` | Remove friendship | `from_classroom_id` |

### AI & Document Management (ChromaDB)

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/documents/upload` | `POST` | Upload and embed documents |
| `/api/documents/query` | `POST` | Query for semantically similar documents |
| `/api/documents/delete` | `DELETE` | Delete documents by ID |
| `/api/documents/info` | `GET` | Get collection statistics |
| `/api/documents/update` | `PUT` | Update existing document embeddings |