from locust import HttpUser, between, task


class LinkShortenerUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task(5)
    def create_public_link(self):
        unique_id = self.environment.runner.user_count if self.environment.runner else 0
        self.client.post(
            "/shorten",
            json={"original_url": f"https://example.com/load/{unique_id}/{self.environment.parsed_options.num_users}"},
            name="POST /shorten",
        )

    @task(2)
    def create_and_fetch_stats(self):
        response = self.client.post(
            "/shorten",
            json={"original_url": "https://example.com/load/stats"},
            name="POST /shorten (stats scenario)",
        )
        if not response.ok:
            return

        short_code = response.json().get("short_code")
        if not short_code:
            return

        self.client.get(f"/{short_code}", allow_redirects=False, name="GET /{short_code}")
        self.client.get(f"/links/{short_code}/stats", name="GET /links/{short_code}/stats")
