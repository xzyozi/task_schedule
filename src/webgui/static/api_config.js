// src/webgui/static/api_config.js

let API_BASE_URL = '';

export async function fetchConfig() {
    if (API_BASE_URL) {
        return API_BASE_URL; // Already fetched
    }
    try {
        const response = await fetch('/webgui-config');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const config = await response.json();
        API_BASE_URL = config.API_BASE_URL;
        return API_BASE_URL;
    } catch (error) {
        console.error('Error fetching webgui configuration:', error);
        // Fallback to a default or handle error appropriately
        API_BASE_URL = '/api';
        return API_BASE_URL;
    }
}

export function getApiBaseUrl() {
    return API_BASE_URL;
}
