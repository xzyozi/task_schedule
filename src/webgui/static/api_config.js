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

/**
 * Escapes HTML special characters to prevent XSS when inserting
 * user-controlled strings via innerHTML.
 * @param {*} value - Value to escape. Non-string values are coerced to string.
 * @returns {string} Escaped string safe for innerHTML interpolation.
 */
export function escapeHtml(value) {
    if (value === null || value === undefined) {
        return '';
    }
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}
