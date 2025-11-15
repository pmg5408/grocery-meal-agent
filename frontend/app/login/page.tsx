"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@/context/userContext';

export default function loginPage() 
{
    const router = useRouter();

    const { login } = useUser();

    const [email, setEmail] = useState<string>('');
    const [password, setPassword] = useState<string>('');

    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (event: React.FormEvent) =>
    {
        event.preventDefault(); //Stop the form from refreshing
        setLoading(true);
        setError(null);

        const loginData = 
        {
            email,
            password,
        };

        try
        {
            const response = await fetch
            (
                'http://127.0.0.1:8000/user/login/',
                {
                    method: 'POST',
                    headers: 
                    {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(loginData),
                }
            );
            if(!response.ok)
            {
                const errorData = await response.json();
                throw new Error(errorData.detail || "Failed to log in");
            }

            const userData = await response.json();
            login(userData);
            router.push('/') //Push is used for redirecting to a different webpage
        }
        catch (err: any)
        {
            setError(err.message);
        }
        finally
        {
            setLoading(false);
        }
    };
    return(
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <div className="max-w-md w-full bg-white p-8 rounded-lg shadow-md">
                <h2 className="text-2xl font-bold text-center text-gray-900 mb-6">
                Log In to Your Account
                </h2>
                
                <form onSubmit={handleSubmit} className="space-y-4">
                
                {/* --- Email Input --- */}
                <div>
                    <label className="block text-sm font-medium text-gray-700">
                    Email
                    </label>
                    <input
                    type="email"
                    value={email} // "Two-Way Binding" (Read)
                    onChange={(e) => setEmail(e.target.value)} // (Write)
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                </div>

                {/* --- Password Input --- */}
                <div>
                    <label className="block text-sm font-medium text-gray-700">
                    Password
                    </label>
                    <input
                    type="password"
                    value={password} // (Read)
                    onChange={(e) => setPassword(e.target.value)} // (Write)
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                </div>

                {/* --- Error Message Display --- */}
                {error && (
                    <p className="text-sm text-red-600">{error}</p>
                )}

                {/* --- Submit Button --- */}
                <div>
                    <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-2 px-4 bg-blue-600 text-white rounded-md
                                disabled:bg-gray-400"
                    >
                    {loading ? 'Logging in...' : 'Log In'}
                    </button>
                </div>
                </form>
            </div>
        </div>
    );
}