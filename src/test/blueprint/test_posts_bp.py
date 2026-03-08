import pytest

from src.app.model.post import Post


@pytest.mark.integration
def test_create_post_persists_post_and_returns_payload(client, auth_token, create_profile):
    token, account = auth_token
    profile = create_profile(account=account, name="Poster")

    response = client.post(
        "/api/posts",
        json={"content": "Hello from integration test", "imageUrl": "https://example.com/img.png"},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert response.status_code == 201, response.get_data(as_text=True)
    payload = response.get_json()
    assert payload["post"]["authorId"] == str(profile.id)
    assert payload["post"]["content"] == "Hello from integration test"

    post_id = int(payload["post"]["id"])
    post = Post.query.get(post_id)
    assert post is not None
    assert post.profile_id == profile.id
    assert post.content == "Hello from integration test"
    assert post.image_url == "https://example.com/img.png"


@pytest.mark.integration
def test_like_and_unlike_post_persist_counter_and_relationship(
    client, auth_token, create_profile, create_post
):
    token, account = auth_token
    profile = create_profile(account=account, name="Poster")
    post = create_post(profile=profile, content="Like me")

    like_response = client.post(
        f"/api/posts/{post.id}/like",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    assert like_response.status_code == 200, like_response.get_data(as_text=True)

    liked_post = Post.query.get(post.id)
    assert liked_post.likes == 1
    assert account in liked_post.liked_by

    unlike_response = client.post(
        f"/api/posts/{post.id}/unlike",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    assert unlike_response.status_code == 200, unlike_response.get_data(as_text=True)

    unliked_post = Post.query.get(post.id)
    assert unliked_post.likes == 0
    assert account not in unliked_post.liked_by


@pytest.mark.integration
def test_get_posts_returns_created_posts(client, auth_token, create_profile, create_post):
    token, account = auth_token
    profile = create_profile(account=account, name="Poster")
    create_post(profile=profile, content="First")
    create_post(profile=profile, content="Second")

    response = client.get(
        "/api/posts",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    payload = response.get_json()
    assert "posts" in payload
    assert len(payload["posts"]) >= 2
