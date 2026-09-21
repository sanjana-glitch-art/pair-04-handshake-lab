const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:9040";


async function request(endpoint, options = {}) {
  const token = localStorage.getItem("access_token");

  const response = await fetch(
    `${API_BASE_URL}${endpoint}`,
    {
      ...options,
      headers: {
        "Content-Type": "application/json",

        ...(token
          ? {
              Authorization: `Bearer ${token}`,
            }
          : {}),

        ...(options.headers || {}),
      },
    }
  );

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    let errorMessage = "Request failed.";

    if (Array.isArray(data?.detail)) {
      errorMessage = data.detail
        .map((error) => {
          const field =
            error.loc?.slice(-1)[0] || "field";

          return `${field}: ${error.msg}`;
        })
        .join(", ");
    } else if (typeof data?.detail === "string") {
      errorMessage = data.detail;
    } else if (data?.detail) {
      errorMessage = JSON.stringify(data.detail);
    }

    throw new Error(errorMessage);
  }

  return data;
}


export function signup(studentData) {
  return request("/auth/signup", {
    method: "POST",
    body: JSON.stringify(studentData),
  });
}


export function login(credentials) {
  return request("/auth/login", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}


export function getMyProfile() {
  return request("/students/me");
}


export function updateMyProfile(profileData) {
  return request("/students/me", {
    method: "PUT",
    body: JSON.stringify(profileData),
  });
}