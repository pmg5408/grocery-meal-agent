"use client";

import { createContext, useState, useContext, ReactNode } from "react";
import { User } from "@/components/types/user"

interface UserContextType {
    user: User | null;
    login: (userData: User) => void;
    logout: () => void;
}

//UserContext is just a container that holds 2 components: UserContext.Provider and UserContext.Consumer
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
        //Using angular brackets is a way of creating react components
        //props can be passed to components. Here we are passing a single prop - value which contains user, login, logout
        //We are wrapping all the children components in this 
        //so that they can obtain data from the value prop
        <UserContext.Provider value={{ user, login, logout }}>
            {children}
        </UserContext.Provider>
    );
};

export function useUser() {
    //useContext() is a modern way of getting a context's consumer
    //So instead of doing UserContext.Consumer we did the below
    const context = useContext(UserContext);

    if (context === undefined)
    {
        throw new Error('useUser must be used within a UserProvider');        
    }

    return context;
}

