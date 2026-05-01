import axios from "axios";

const API_BASE = "http://127.0.0.1:8000";

export async function askAI(query) {
    const response = await axios.post(
        `${API_BASE}/api/ask`,
        new URLSearchParams({ query }),
        {
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
            },
        }
    );

    return response.data;
}

export async function searchTrains(filters) {
    const response = await axios.get(`${API_BASE}/api/search`, {
        params: filters,
    });

    return response.data.results;
}

export async function getRealtime(city) {
    const response = await axios.get(`${API_BASE}/api/realtime`, {
        params: { city },
    });

    return response.data;
}
export async function getSeats(routeId) {
    const response = await axios.get(`${API_BASE}/api/seats/${routeId}`);
    return response.data.seats;
}

export async function bookTicket(payload) {
    const response = await axios.post(`${API_BASE}/api/book`, payload);
    return response.data;
}

