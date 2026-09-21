const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:9040";

async function request(endpoint, options = {}) {
  const token = localStorage.getItem("access_token");

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
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
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    let message = "Request failed.";

    if (typeof data?.detail === "string") {
      message = data.detail;
    } else if (Array.isArray(data?.detail)) {
      message = data.detail
        .map((item) => item.msg || "Invalid input")
        .join(", ");
    } else if (data?.detail) {
      message = JSON.stringify(data.detail);
    }

    throw new Error(message);
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

export function searchJobs(filters = {}) {
  const params = new URLSearchParams();

  if (filters.search) {
    params.append("search", filters.search);
  }

  if (filters.category) {
    params.append("category", filters.category);
  }

  if (filters.city) {
    params.append("city", filters.city);
  }

  // Only send valid boolean values.
  if (filters.remote === "true" || filters.remote === "false") {
    params.append("remote", filters.remote);
  }

  if (filters.min_salary) {
    params.append("min_salary", filters.min_salary);
  }

  const queryString = params.toString();

  return request(queryString ? `/jobs?${queryString}` : "/jobs");
}

export function getJobDetails(jobId) {
  return request(`/jobs/${jobId}`);
}