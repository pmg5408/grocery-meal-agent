"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function RegisterPage() 
{

    const router = useRouter();

    const [email, setEmail] = useState<string>('');
    const [password, setPassword] = useState<string>('');
    const [firstName, setFirstName] = useState<string>('');
    const [lastName, setLastName] = useState<string>('');

    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (event: React.FormEvent) => 
    {
        event.preventDefault();
        setLoading(true);
        setError(null);

        const UserData = 
        {
            email,  
            firstName,
            lastName,
            password,
        };

        try
        {
            const response = await fetch
            ('http://127.0.0.1:8000/user/register/', 
                {
                    method: 'POST',
                    headers: 
                    {
                      'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(UserData),
                }
            );

            if(!response.ok)
            {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to register');
            }

            const newUser = await response.json();
            alert('Registration successful! Please log in.');
            router.push('/login');
        }
        catch(err: any)
        {
            setError(err.message);
        }
        finally
        {
            setLoading(false);
        }
    };
    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="max-w-md w-full bg-white p-8 rounded-lg shadow-md">
            <h2 className="text-2xl font-bold text-center text-gray-900 mb-6">
              Register New Account
            </h2>
            
            {/*
             * This is the "textbook" React form.
             * - 'onSubmit={handleSubmit}': We "wire" the form's
             * 'submit' event to our 'handleSubmit' function.
             * When the user clicks the 'submit' button, React
             * will call 'handleSubmit'.
             */}
            <form onSubmit={handleSubmit} className="space-y-4">
              
              {/* --- First Name Input --- */}
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  First Name
                </label>
                <input
                  type="text"
                  // 'value={firstName}': "Two-Way Binding" (Part 1)
                  // The *value* of this input is "bound" to
                  // our 'firstName' state variable.
                  value={firstName}
                  // 'onChange={...}': "Two-Way Binding" (Part 2)
                  // When the user types, this 'onChange' event
                  // fires. We call 'setFirstName' to update
                  // our "memory" with the new value ('e.target.value').
                  onChange={(e) => setFirstName(e.target.value)}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Last Name
                </label>
                <input
                  type="text"
                  // 'value={firstName}': "Two-Way Binding" (Part 1)
                  // The *value* of this input is "bound" to
                  // our 'firstName' state variable.
                  value={lastName}
                  // 'onChange={...}': "Two-Way Binding" (Part 2)
                  // When the user types, this 'onChange' event
                  // fires. We call 'setFirstName' to update
                  // our "memory" with the new value ('e.target.value').
                  onChange={(e) => setLastName(e.target.value)}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              
              {/* --- Email Input --- */}
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Email
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
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
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
    
              {/* --- Error Message Display --- */}
              {/* This is "conditional rendering."
               * '{error && ...}' is JavaScript syntax that means:
               * "If 'error' is a "truthy" value (not 'null'),
               * *then* render the <p> tag."
               */}
              {error && (
                <p className="text-sm text-red-600">{error}</p>
              )}
    
              {/* --- Submit Button --- */}
              <div>
                <button
                  type="submit"
                  // We "disable" the button if 'loading' is true
                  // to prevent the user from clicking it twice.
                  disabled={loading}
                  className="w-full py-2 px-4 bg-blue-600 text-white rounded-md
                             disabled:bg-gray-400"
                >
                  {/* This is "conditional rendering" for the text.
                   * We use a "ternary operator" ( condition ? A : B )
                   * If 'loading' is true, show "Registering..."
                   * Otherwise ('loading' is false), show "Register".
                   */}
                  {loading ? 'Registering...' : 'Register'}
                </button>
              </div>
            </form>
          </div>
        </div>
    ); 
}