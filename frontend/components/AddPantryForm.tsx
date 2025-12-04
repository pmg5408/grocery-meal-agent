"use client"

import React, { useState } from 'react';

interface AddPantryProps 
{
    onSuccess: () => void,
    onCancel: () => void,
}

export default function AddPantry({onSuccess, onCancel} : AddPantryProps) 
{
    const [pantryNickname, setPantryNickname] = useState<string>('');
    
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    const handlePantryAdd = async(event: React.FormEvent) => 
    {
        event.preventDefault();
        setLoading(true);
        setError(null);

        const pantryData = 
        {
            pantryNickname: pantryNickname
        }

        try
        {
            const response = await fetch
            (
                'http://127.0.0.1:8000/pantry',
                {
                    method: 'POST',
                    headers: 
                    {
                        'Authorization': `Bearer ${localStorage.getItem("jwt")}`,
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(pantryData) //Need to add the data here
                }
            );

            if (!response.ok)
            {
                throw new Error('Failed to add new pantry');
            }

            onSuccess();
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

    return (
        // 'onSubmit={handleSubmit}' wires the form
        // to our submit logic function.
        <form onSubmit={handlePantryAdd} className="space-y-4">
        
        {/* --- Pantry Name Input --- */}
        <div>
            <label className="block text-sm font-medium text-gray-700">
            Pantry Name
            </label>
            <input
            type="text"
            value={pantryNickname} // "Two-Way Binding" (Read from state)
            onChange={(e) => setPantryNickname(e.target.value)} // (Write to state)
            required
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
        </div>

        {/* --- Error Message Display --- */}
        {error && (
            <p className="text-sm text-red-600">{error}</p>
        )}

        {/* --- Action Buttons --- */}
        <div className="flex justify-end space-x-3 pt-4">
            
            {/*
            * This button has 'type="button"'. This is
            * CRITICAL. It *prevents* this button from
            * submitting the form. Its *only* job
            * is to call 'onCancel'.
            */}
            <button
            type="button" 
            onClick={onCancel} // Calls the parent's "close modal" function
            className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300"
            >
            Cancel
            </button>
            
            {/*
            * This button has 'type="submit"'. This is the
            * *default* for a button in a form.
            * Clicking it will trigger the 'onSubmit'
            * event on the '<form>' tag.
            */}
            <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-md disabled:bg-gray-400"
            >
            {loading ? 'Creating...' : 'Create Pantry'}
            </button>
        </div>
        </form>
    );
}