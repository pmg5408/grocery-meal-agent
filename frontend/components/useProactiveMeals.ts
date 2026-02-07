import { useState, useRef, useEffect } from 'react';
import { ProactiveMealDisplayData } from "@/components/types/recipes";
import { User } from "@/components/types/user";

export default function useProactiveMeals(user: User | null) 
{
    const [proactiveMeals, setProactiveMeals] = useState<ProactiveMealDisplayData | null>(null);
    const [connectionStatus, setConnectionStatus] =
        useState<"connecting" | "connected" | "disconnected">("connecting");

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const eventSourceRef = useRef<EventSource | null>(null);

    // -------- FETCH MEALS (reusable helper) ----------
    const fetchLatestMeals = async () => {
        try {
            setLoading(true);
            setError(null);

            const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;
            const API_PROTOCOL = process.env.NEXT_PUBLIC_API_PROTOCOL || 'http';
            const response = await fetch(
                `${API_PROTOCOL}://${API_BASE_URL}/proactiveMeals/`,
                {
                    headers: {
                        Authorization: `Bearer ${localStorage.getItem("jwt")}`,
                    }
                }
            );

            if (!response.ok) {
                throw new Error("Failed to fetch proactive meals");
            }

            const data: ProactiveMealDisplayData = await response.json();
            setProactiveMeals(data);
        }
        catch (err: any) {
            setError(err.message);
        }
        finally {
            setLoading(false);
        }
    };

    // -------- INIT SSE ----------
    function initSSE() {
        const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;
        const API_PROTOCOL = process.env.NEXT_PUBLIC_API_PROTOCOL || 'http';
        const token = localStorage.getItem("jwt");
        
        // EventSource doesn't support custom headers, so we pass token in URL
        const sseUrl = `${API_PROTOCOL}://${API_BASE_URL}/events?token=${token}`;
        
        const es = new EventSource(sseUrl);
        eventSourceRef.current = es;

        es.onopen = () => {
            console.log("🔌 SSE connected");
            setConnectionStatus("connected");
        };

        es.onerror = (error) => {
            console.error("SSE error:", error);
            setConnectionStatus("disconnected");
            // EventSource will automatically try to reconnect
        };

        // Listen for the initial connection event
        es.addEventListener('connected', (event) => {
            console.log("✅ SSE connection established:", event.data);
        });

        // Listen for meal ready events
        es.addEventListener('meal_ready', (event) => {
            console.log("📩 SSE: new meal generated → refetching...");
            fetchLatestMeals();
        });
    }

    // -------- EFFECT: On first mount + when user logs in ----------
    useEffect(() => {
        if (!user) {
            if (eventSourceRef.current) {
                eventSourceRef.current.close();
                eventSourceRef.current = null;
            }
            setConnectionStatus("disconnected");
            setProactiveMeals(null);
            return;
        }

        // 1) Fetch meals immediately on page load or login
        fetchLatestMeals();

        // 2) Open SSE connection
        initSSE();

        return () => {
            if (eventSourceRef.current) {
                eventSourceRef.current.close();
                eventSourceRef.current = null;
            }
        };
    }, [user]);

    return {
        proactiveMeals,
        connectionStatus,
        loading,
        error,
        setProactiveMeals,
    };
}
