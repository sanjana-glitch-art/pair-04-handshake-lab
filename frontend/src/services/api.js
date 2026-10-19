export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:9040";

// Turns a stored relative upload path into a URL the browser can load.
export function uploadUrl(path) {
  return path ? `${API_BASE_URL}/${path}` : "";
}

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

  // An expired or invalid session: drop the token and go back to login
  // instead of leaving the user on a page that can only show errors.
  if (response.status === 401 && token && !endpoint.startsWith("/auth/")) {
    localStorage.removeItem("access_token");
    window.location.assign("/login");
  }

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

export function companySignup(companyData) {
  return request("/auth/company/signup", {
    method: "POST",
    body: JSON.stringify(companyData),
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

export async function submitApplication(jobId, resumeFile) {
  const token = localStorage.getItem("access_token");

  const formData = new FormData();

  formData.append("job_id", jobId);
  formData.append("resume", resumeFile);

  const response = await fetch(`${API_BASE_URL}/applications`, {
    method: "POST",
    headers: {
      ...(token
        ? {
            Authorization: `Bearer ${token}`,
          }
        : {}),
    },
    body: formData,
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    let message = "Unable to submit application.";

    if (typeof data?.detail === "string") {
      message = data.detail;
    } else if (Array.isArray(data?.detail)) {
      message = data.detail
        .map((item) => item.msg || "Invalid input")
        .join(", ");
    }

    throw new Error(message);
  }

  return data;
}

export function getMyApplications(status = "") {
  return request(
    status
      ? `/applications/me?status=${encodeURIComponent(status)}`
      : "/applications/me"
  );
}

export function getEvents(filters = {}) {
  const params = new URLSearchParams();

  if (filters.search) {
    params.append("search", filters.search);
  }

  if (filters.city) {
    params.append("city", filters.city);
  }

  const queryString = params.toString();

  return request(
    queryString ? `/events?${queryString}` : "/events"
  );
}

export function registerForEvent(eventId) {
  return request(`/events/${eventId}/register`, {
    method: "POST",
  });
}

export function getRegisteredEvents() {
  return request("/events/registered");
}

export function getMyPreferences() {
  return request("/preferences/me");
}

export function updateMyPreferences(preferenceData) {
  return request("/preferences/me", {
    method: "PUT",
    body: JSON.stringify(preferenceData),
  });
}

export function chatWithAssistant(message, history = []) {
  return request("/assistant/chat", {
    method: "POST",
    body: JSON.stringify({
      message,
      history,
    }),
  });
}

export function getEmployerJobs() {
  return request("/employer/jobs");
}

export function createEmployerJob(jobData) {
  return request("/employer/jobs", {
    method: "POST",
    body: JSON.stringify(jobData),
  });
}

export function updateEmployerJob(jobId, jobData) {
  return request(`/employer/jobs/${jobId}`, {
    method: "PUT",
    body: JSON.stringify(jobData),
  });
}

export function deleteEmployerJob(jobId) {
  return request(`/employer/jobs/${jobId}`, {
    method: "DELETE",
  });
}

export function getEmployerEvents() {
  return request("/employer/events");
}

export function createEmployerEvent(eventData) {
  return request("/employer/events", {
    method: "POST",
    body: JSON.stringify(eventData),
  });
}

export function updateEmployerEvent(eventId, eventData) {
  return request(`/employer/events/${eventId}`, {
    method: "PUT",
    body: JSON.stringify(eventData),
  });
}

export function deleteEmployerEvent(eventId) {
  return request(`/employer/events/${eventId}`, {
    method: "DELETE",
  });
}

export function getEmployerApplications() {
  return request("/employer/applications");
}

export function getEmployerApplication(applicationId) {
  return request(`/employer/applications/${applicationId}`);
}

export function updateEmployerApplicationStatus(
  applicationId,
  status
) {
  return request(
    `/employer/applications/${applicationId}/status`,
    {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }
  );
}

export function getEmployerProfile() {
  return request("/employer/profile");
}

export function updateEmployerProfile(profileData) {
  return request("/employer/profile", {
    method: "PUT",
    body: JSON.stringify(profileData),
  });
}

// Sends a file with multipart/form-data. The JSON helper above would set
// the wrong Content-Type, so uploads use their own fetch.
async function uploadFile(endpoint, fieldName, file) {
  const token = localStorage.getItem("access_token");
  const formData = new FormData();

  formData.append(fieldName, file);

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(
      typeof data?.detail === "string" ? data.detail : "Upload failed."
    );
  }

  return data;
}

export function uploadMyProfilePicture(file) {
  return uploadFile("/students/me/picture", "picture", file);
}

export function uploadEmployerPicture(file) {
  return uploadFile("/employer/profile/picture", "picture", file);
}

export function searchStudents(filters = {}) {
  const params = new URLSearchParams();

  for (const key of ["name", "college", "major", "skill"]) {
    if (filters[key]) {
      params.append(key, filters[key]);
    }
  }

  const queryString = params.toString();

  return request(queryString ? `/students?${queryString}` : "/students");
}

export function getStudentMajors() {
  return request("/students/majors");
}

export function getStudentProfile(studentId) {
  return request(`/students/${studentId}`);
}

export function getEventDetails(eventId) {
  return request(`/events/${eventId}`);
}

export function getEventRegistrations(eventId) {
  return request(`/employer/events/${eventId}/registrations`);
}

export function getEmployerApplicationsFiltered(filters = {}) {
  const params = new URLSearchParams();

  if (filters.jobId) {
    params.append("job_id", filters.jobId);
  }

  if (filters.status) {
    params.append("status", filters.status);
  }

  const queryString = params.toString();

  return request(
    queryString
      ? `/employer/applications?${queryString}`
      : "/employer/applications"
  );
}

// Resumes are private, so they are fetched with the token and shown
// through a temporary object URL instead of a public link.
export async function fetchResumeBlobUrl(applicationId) {
  const token = localStorage.getItem("access_token");

  const response = await fetch(
    `${API_BASE_URL}/employer/applications/${applicationId}/resume`,
    {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    }
  );

  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(data?.detail || "Could not load the resume.");
  }

  return URL.createObjectURL(await response.blob());
}
