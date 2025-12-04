import { useState, useRef, useEffect } from 'react';
import { ProactiveMealDisplayData } from "@/components/types/recipes";
import { User } from "@/components/types/user";

interface ProactiveMealDataForGetReq{
    mealWindow: string;
}

export default function useProactiveMeals(user: User | null) 
{
    const [proactiveMeals, setProactiveMeals] = useState<ProactiveMealDisplayData | null>(null);
    const [connectionStatus, setConnectionStatus] =
        useState<"connecting" | "connected" | "disconnected">("connecting");

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>('');
 
    const wsRef = useRef<WebSocket | null>(null);

    function initWebSocket() 
    {
        const wsUrl = `ws://localhost:8000/ws?token=${localStorage.getItem("jwt")}`;
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
            console.log("🔌 WebSocket connected for proactive meals");
            setConnectionStatus("connected");
        };

        ws.onclose = () => {
            setConnectionStatus("disconnected");
        }

        ws.onerror = () => {
            setConnectionStatus("disconnected");
        }

        /*
        Remember that useEffect runs once on the first render and then whenever it's deps [] change
        We want to setup ws once and not on every render
        So useEffect runs once on first render and sets up the web socket
        and after that only if the user changes
        During the setup of the websocket it is registered with the browser
        React does not handle anything related to it
        So the callback function associated with onmessage lives even after useEffect is done executing
        */ 
        ws.onmessage = async (event) => 
        /*
        In the web socket message we dont want to send the full payload
        we only tell the frontend that there is a new meal ready
        come fetch it.
        So event.data only contains the mealWindow
        Then using fetch the frontend goes and gets the full payload
        */
        {
            setLoading(true);
            setError(null)
            try 
            {
                const data: ProactiveMealDataForGetReq = JSON.parse(event.data);
                console.log("📩 Received proactive meal event:", data);

                const response = await fetch(
                    `http://localhost:8000/proactiveMeals/latest?mealWindow=${data.mealWindow}`,
                    {
                        headers:
                        {
                            Authorization: `Bearer ${localStorage.getItem("jwt")}`,
                        },
                    }
                );
                if (!response.ok) {
                    console.error("Failed to fetch latest proactive meals");
                    return;
                }

                const mealData: ProactiveMealDisplayData = await response.json();

                setProactiveMeals(mealData);
            }
            catch(err: any)
            {
                setError(err.message);
            }
            finally
            {
                setLoading(false);
            }
        }
    }

    useEffect(() => {
        if(!user)
        {
            // Close existing connection if user logs out
            if (wsRef.current) {
                wsRef.current.close(1000, "User logged out");
                wsRef.current = null;
            }
            setConnectionStatus("disconnected");
            return;
        }
        
        initWebSocket();

        return () => 
        {
            if (wsRef.current) 
            {
                wsRef.current.close(1000, "Component unmounting");
            }
        };
    }, [user]);

    return {
        proactiveMeals,
        connectionStatus,
        loading,
        error,
        setProactiveMeals
    };
}