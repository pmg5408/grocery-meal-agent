"use client";

import { createContext, useState, useContext, ReactNode, Children } from "react";

interface User {
    id: number;
    email: string;
    firstName: string;
    lastName: string;
}

interface UserContextType {
    user: User | null;
    login: (userData: User) => void;
    logout: () => void;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export function UserProvider({ children }: { children: ReactNode })
{
    const [user, setUser] = useState<User | null>(null);

    const login = (userData: User) => {
        setUser(userData);
    };

    const logout = () => {
        setUser(null);
    };

    return(
        <UserContext.Provider value={{ user, login, logout }}>
            {children}
        </UserContext.Provider>
    );
};

export function useUser() {
    const context = useContext(UserContext);

    if (context === undefined)
    {
        throw new Error('useUser must be used within a UserProvider');        
    }

    return context;
}

