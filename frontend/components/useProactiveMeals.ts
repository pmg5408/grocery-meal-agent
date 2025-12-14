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

    const wsRef = useRef<WebSocket | null>(null);

    // -------- FETCH MEALS (reusable helper) ----------
    const fetchLatestMeals = async () => {
        try {
            setLoading(true);
            setError(null);

            const response = await fetch(
                `http://localhost:8000/proactiveMeals/`,
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

    // -------- INIT WEBSOCKET ----------
    function initWebSocket() {
        const wsUrl = `ws://localhost:8000/ws?token=${localStorage.getItem("jwt")}`;
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
            console.log("🔌 WS connected");
            setConnectionStatus("connected");
        };

        ws.onclose = () => setConnectionStatus("disconnected");
        ws.onerror = () => setConnectionStatus("disconnected");

        ws.onmessage = () => {
            // no meal window needed anymore
            console.log("📩 WS: new meal generated → refetching...");
            fetchLatestMeals();
        };
    }

    // -------- EFFECT: On first mount + when user logs in ----------
    useEffect(() => {
        if (!user) {
            if (wsRef.current) {
                wsRef.current.close(1000, "User logged out");
                wsRef.current = null;
            }
            setConnectionStatus("disconnected");
            setProactiveMeals(null);
            return;
        }

        // 1) Fetch meals immediately on page load or login
        fetchLatestMeals();

        // 2) Open WS connection
        initWebSocket();

        return () => {
            if (wsRef.current) {
                wsRef.current.close(1000, "Component unmount");
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
