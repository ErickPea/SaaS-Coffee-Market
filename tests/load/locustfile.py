from locust import HttpUser, task, between


class CoffeeMarketUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def ver_dashboard(self):
        self.client.get("/api/prices/national")
        self.client.get("/api/prices/international")
        self.client.get("/api/currency")

    @task(1)
    def ver_historial(self):
        self.client.get("/api/prices/history?market=nacional&period=30d")

    @task(1)
    def calcular_simulacion(self):
        self.client.post("/api/investment/calculate", json={
            "hectares": 5,
            "production_per_hectare_kg": 1500,
            "use_current_price": True,
            "costs": {},
        })