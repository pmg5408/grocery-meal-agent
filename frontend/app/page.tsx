"use client";

import { useRouter } from "next/navigation";
import { useUser } from "@/context/userContext";
import { useState, useEffect } from "react";

import PantryAccordion from '@/components/PantryAccordion';
import { arrayBuffer } from "stream/consumers";

interface Pantry{
  pantryNickname: string,
  pantryId: number,
  userId: number,
}

export default function Home()
{
  const router = useRouter();
  const { user } = useUser();

  const [pantries, setPantries] = useState<Pantry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [isSelectionMode, setIsSelectionMode] = useState(false);
  const [selectedItemIds, setSelectedItemIds] = useState<Set<number>>( new Set());

  const [suggestionLoading, setSuggestionLoading] = useState(false);
  const [suggestionResult, setSuggestionResult] = useState<any>(null);

  const handleItemSelectToggle = (pantryItemId: number) => 
  {
    const newSelectedIds = new Set(selectedItemIds);

    if (newSelectedIds.has(pantryItemId)) 
    {
      newSelectedIds.delete(pantryItemId);
    }
    else
    {
      newSelectedIds.add(pantryItemId);
    }

    setSelectedItemIds(newSelectedIds);
  } 

  const handleSuggestedMeals = async() =>
  {
    setSuggestionLoading(true);
    setSuggestionResult(null);
    setError(null);

    const requestData = 
    {
      priorityPantryItemIds: Array.from(selectedItemIds),
      priorityPantryIds: [],
    }

    try
    {
      const response = await fetch
      (
        'http://127.0.0.1:8000/pantry/suggestMeal',
        {
          method: 'POST',
          headers:
          {
            'Content-type': 'application/json'
          },
          body: JSON.stringify(requestData)
        }
      );

      if(!response.ok)
      {
        throw new Error('Encountered an error while trying to generate recipes');
      }

      const recipes = await response.json();
      setSuggestionResult(recipes);
      setIsSelectionMode(false);
      setSelectedItemIds(new Set());

    }
    catch(err: any)
    {
      setError(err.message);
    }
    finally
    {
      setSuggestionLoading(false);
    }
  };

  useEffect(() => 
  {
    if(!user) 
    {
      router.push("/login");
      return;
    }

    const fetchPantries = async () => 
    {
      try
      {
        setLoading(true);
        setError(null);

        const response = await fetch('http://127.0.0.1:8000/pantries/');

        if(!response.ok)
        {
          throw new Error('Failed to etch pantries');
        }

        const data: Pantry[] = await response.json();
        setPantries(data);
      }
      catch (err: any)
      {
        setError(err.message);
      }
      finally
      {
        setLoading(false);
      }
    }
    fetchPantries();
  }, [user, router]);

  if (!user) 
  {
    return (
      <div className="min-h-screen flex items-center justify-center">
        Loading...
      </div>
    );
  }

  // Show a "Loading..." message while we are fetching pantries
  if (loading) 
  {
     return (
      <div className="min-h-screen flex items-center justify-center">
        Loading your dashboard...
      </div>
    );
  }

  // Show an error if the 'fetchPantries' call failed
  if (error) 
  {
    return (
      <div className="min-h-screen flex items-center justify-center text-red-600">
        Error: {error}
      </div>
    );
  }

  // --- The "Happy Path" (We are logged in, data is loaded) ---
  return (
    <main className="min-h-screen p-8 sm:p-24 bg-gray-50">
      <div className="max-w-4xl">
        <h1 className="text-4xl font-bold">
          Welcome, {user.firstName}!
        </h1>

        {/* --- This is the new part: The Pantry List --- */}
        <div className="mt-10">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-semibold">Your Pantries</h2>
            {/* This is the button for YOUR "Story 3".
              We'll add the 'onClick' for it *next*.
              For now, it's just a placeholder.
            */}
            <button 
              onClick={() => setIsSelectionMode(!isSelectionMode)}
              className="px-4 py-2 bg-blue-600 text-white rounded-md shadow hover:bg-blue-700">
              {isSelectionMode? 'Cancel Selection' : 'Select Items for Recipe'}
            </button>
          </div>
          
          {/* Conditional Rendering */}
          {pantries.length === 0 ? (
            <p className="mt-2 text-gray-500">
              You haven't created any pantries yet.
            </p>
          ) : (
            <ul className="space-y-3">
              {/* * We "map" (loop) over our 'pantries' state
               * and render ONE 'PantryAccordion' component
               * for *each* pantry in the list.
               */}
              {pantries.map((pantry) => (
                <PantryAccordion 
                  key={pantry.pantryId} 
                  pantry={pantry} 

                  isSelectionMode={isSelectionMode}
                  selectedItemIds={selectedItemIds}
                  onItemSelectToggle={handleItemSelectToggle}
                />
              ))}
            </ul>
          )}
        </div>
      {/* --- ADD THIS ENTIRE NEW BLOCK --- */}
      {/*
        * This is the "Submit" section.
        * It is "conditionally rendered" and will *only* appear
        * if 'isSelectionMode' is true.
        */}
      {isSelectionMode && (
        <div className="mt-8 p-4 bg-white shadow rounded-lg">
          <h3 className="text-lg font-semibold">
            {/* We show a live count of selected items */}
            {selectedItemIds.size} item(s) selected
          </h3>
          <p className="text-sm text-gray-600">
            Click the button to get meal suggestions based
            on your selection.
          </p>
          <button
            onClick={handleSuggestedMeals}
            disabled={suggestionLoading || selectedItemIds.size === 0}
            className="mt-4 w-full py-2 px-4 bg-green-600 text-white rounded-md
                       disabled:bg-gray-400 hover:bg-green-700"
          >
            {suggestionLoading ? 'Thinking...' : 'Suggest Meal!'}
          </button>
        </div>
      )}

      {/* --- ADD THIS BLOCK TO SHOW THE RESULT --- */}
      {/* This block will appear after the API call finishes */}
      {suggestionResult && (
        <div className="mt-8 p-4 bg-white shadow rounded-lg">
          <h3 className="text-lg font-bold">Meal Suggestion Data:</h3>
          {/* A '<pre>' tag is the best way to show raw JSON */}
          <pre className="text-sm bg-gray-900 text-green-300 p-2 rounded overflow-auto">
            {JSON.stringify(suggestionResult, null, 2)}
          </pre>
        </div>
      )}        
      </div>
    </main>
  );
}