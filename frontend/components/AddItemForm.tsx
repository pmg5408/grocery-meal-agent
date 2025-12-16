"use client";

import React, { useState } from "react";

interface Pantry
{
    pantryNickname: string,
    pantryId: number,
    userId: number,
}

interface AddItemProps
{
    pantries: Pantry[],
    onSuccess: () => void;
    onCancel: () => void;
};

export default function AddItemForm({pantries, onSuccess, onCancel}: AddItemProps)
{
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    const [selectedPantryId, setSelectedPantryId] = useState<number | string>( pantries[0]?.pantryId || '');
    const [itemName, setItemName] = useState<string>('');
    const [brand, setBrand] = useState<string>('');
    const [unit, setUnit] = useState<string>('');
    const [quantity, setQuantity] = useState<number>(0);
    const [purchaseDate, setPurchaseDate] = useState(new Date().toISOString().split('T')[0]);

    const itemData = 
    {
        itemName: itemName,
        brand: brand || null,
        quantity: Number(quantity),
        unit: unit || null,
        purchaseDate: new Date(purchaseDate).toISOString()
    }

    const handleItemAdd = async(event: React.FormEvent) => 
    {
        event.preventDefault();

        setLoading(true);
        setError(null);

        try
        {
            const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;
            const response = await fetch
            (
                `http://${API_BASE_URL}/pantry/${selectedPantryId}/item`,
                {
                    method: 'POST',
                    headers:
                    {
                        'Authorization': `Bearer ${localStorage.getItem("jwt")}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(itemData)
                }
            )
    
            if(!response.ok)
            {
                throw new Error('Failed to add item to pantry');
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
    return(
        <form onSubmit={handleItemAdd} className="space-y-4">
        
        {/* --- This is the "Pantry" <select> dropdown --- */}
        <div>
            <label className="block text-sm font-medium text-gray-700">
            Select Pantry
            </label>
            <select
            // The value is "controlled" by our 'selectedPantryId' state
            value={selectedPantryId}
            // 'onChange' updates the state
            onChange={(e) => setSelectedPantryId(e.target.value)}
            required
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
            {pantries.length === 0 ? (
                // Show this if the 'pantries' prop is an empty list
                <option value="" disabled>You must create a pantry first</option>
            ) : (
                // We "map" over the 'pantries' prop (from 'page.tsx')
                // to build the list of <option> tags.
                pantries.map(pantry => (
                <option key={pantry.pantryId} value={pantry.pantryId}>
                    {pantry.pantryNickname}
                </option>
                ))
            )}
            </select>
        </div>

        {/* --- Item Name Input --- */}
        <div>
            <label className="block text-sm font-medium text-black">
            Item Name
            </label>
            <input
            type="text"
            value={itemName}
            onChange={(e) => setItemName(e.target.value)}
            required
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
            placeholder="e.g., Organic Milk"
            />
        </div>

        {/* --- Brand Input --- */}
        <div>
            <label className="block text-sm font-medium text-black">
            Brand (Optional)
            </label>
            <input
            type="text"
            value={brand}
            onChange={(e) => setBrand(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
            placeholder="e.g., Stonyfield"
            />
        </div>

        <div>
            <label className="block text-sm font-medium text-black">
            Unit (Optional)
            </label>
            <input
            type="text"
            value={unit}
            onChange={(e) => setUnit(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
            placeholder="e.g., Stonyfield"
            />
        </div>


        {/* This 'flex' container puts the next two inputs side-by-side */}
        <div className="flex space-x-4">
            
            {/* --- Quantity Input --- */}
            <div className="w-1/2">
            <label className="block text-sm font-medium text-black">
                Quantity
            </label>
            <input
                type="number"
                value={quantity}
                // 'e.target.value' is a string, so we convert it
                onChange={(e) => setQuantity(Number(e.target.value))}
                required
                min="1" // Standard HTML to prevent '0' or negative
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
            </div>
            
            {/* --- Purchase Date Input --- */}
            <div className="w-1/2">
            <label className="block text-sm font-medium text-gray-700">
                Purchase Date
            </label>
            <input
                type="date"
                value={purchaseDate}
                onChange={(e) => setPurchaseDate(e.target.value)}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
            </div>
        </div>

        {/* --- Error Message Display --- */}
        {error && (
            <p className="text-sm text-red-600">{error}</p>
        )}

        {/* --- Action Buttons --- */}
        <div className="flex justify-end space-x-3 pt-4">
            <button
            type="button" // 'type="button"' stops it from submitting
            onClick={onCancel} // Calls the parent's "close modal" function
            className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300"
            >
            Cancel
            </button>
            <button
            type="submit"
            // We disable the button if loading, or if no
            // pantry is selected (which can happen if
            // the 'pantries' list was empty)
            disabled={loading || !selectedPantryId}
            className="px-4 py-2 bg-green-600 text-white rounded-md disabled:bg-gray-400"
            >
            {loading ? 'Adding...' : 'Add Item'}
            </button>
        </div>
        </form>
    );
}