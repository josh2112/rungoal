import axios from "axios";
import { defineStore } from "pinia";
import { ref } from "vue";
import type { ErrorResponse } from "../models";

export const useApi = defineStore("api", () => {
    const api = axios.create({
        baseURL: `${import.meta.env.BASE_URL}/api`,
        withCredentials: true,
        headers: {
            post: {
                "Content-Type": "application/json",
            },
        },
    });

    const errors = ref<ErrorResponse[]>([]);

    const accessToken = ref<string | null>(null);

    // A flag to prevent multiple refresh requests firing at once
    let isRefreshing = false;
    // A queue to hold pending requests while the token is refreshing
    let failedQueue: Array<{ resolve: Function; reject: Function }> = [];

    const processQueue = (error: any, token: string | null = null) => {
        if (failedQueue.length) {
            console.log(
                `Reprocessing ${failedQueue.length} queued requests...`,
            );
        }
        failedQueue.forEach((prom) => {
            if (error) {
                prom.reject(error);
            } else {
                prom.resolve(token);
            }
        });
        failedQueue = [];
    };

    // Add the access token to every request
    api.interceptors.request.use(
        (config) => {
            if (accessToken.value && config.headers) {
                config.headers.Authorization = `Bearer ${accessToken.value}`;
            }
            return config;
        },
        (error) => Promise.reject(error),
    );

    api.interceptors.response.use(
        (response) => response,
        async (error) => {
            const originalRequest = error.config;

            // Access token expired?
            if (error.response.status == 401 && !originalRequest._retry) {
                originalRequest._retry = true;

                // If a refresh is already happening, queue this request until it finishes
                if (isRefreshing) {
                    return new Promise(function (resolve, reject) {
                        failedQueue.push({ resolve, reject });
                    })
                        .then((token) => {
                            originalRequest.headers.Authorization = `Bearer ${token}`;
                            return api(originalRequest);
                        })
                        .catch((err) => {
                            return Promise.reject(err);
                        });
                }

                isRefreshing = true;

                try {
                    console.log("Attempting credential refresh...");
                    const refreshResponse = await axios.post(
                        `${import.meta.env.BASE_URL}/api/auth/refresh`,
                        {},
                        { withCredentials: true },
                    );

                    console.log("Credentials obtained");
                    accessToken.value = refreshResponse.data.access_token;

                    // Process the queued requests with the new token
                    processQueue(null, accessToken.value);

                    // Retry the original request
                    originalRequest.headers.Authorization = `Bearer ${accessToken.value}`;
                    return api(originalRequest);
                } catch (refreshError) {
                    // If the refresh token is also expired/invalid, the user must log in again
                    processQueue(refreshError, null);

                    // Clear local storage and redirect to login
                    accessToken.value = null;

                    return Promise.reject(refreshError);
                } finally {
                    isRefreshing = false;
                }
            } else if (error.response.data) {
                errors.value.push(error.response.data as ErrorResponse);
            }

            return Promise.reject(error);
        },
    );

    return { get: api.get, post: api.post, accessToken, errors };
});
