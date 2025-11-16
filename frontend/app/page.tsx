"use client";

import { useRouter } from "next/navigation";
import { useUser } from "@/context/userContext";
import { useState, useEffect } from "react";

import PantryAccordion from '@/components/PantryAccordion';
import AddPantryForm from '@/components/AddPantryForm';
import AddItemForm from '@/components/AddItemForm';

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
  const [selectedItemIds, setSelectedItemIds] = useState<Set<number>>(new Set());

  const [suggestionLoading, setSuggestionLoading] = useState(false);
  const [suggestionResult, setSuggestionResult] = useState<any>(null);

  const [modalView, setModalView] = useState<'closed' | 'add' | 'addPantry' | 'addItem'>('closed');

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

    //This is like a dictionary
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
            'Content-Type': 'application/json'
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

  /*
  use effect is meant to be used for code that causes side effects like fetching, timers
  useEffect gets executed once AFTER the first render of the UI
  After that, it only executes if the states in the list at the end of function change
  in our case they are: user and router

  we use useEffect for this fetch and not for other fetches because
  we want to display pantries(and in turn fetch pantries) when the page is loaded
  compared to other fetches that we are doing when a button is clicked
  so those fetches are controlled
  and useEffect gives us a way to control an automatic fetch
  and not fetch everytime main component is rendered
  */

  const fetchPantries = async () => 
  {
    try
    {
      /*
      Changing the state like we are doing in the below 2 lines
      cause the main component to re-render but since we have this wrapped in user effect
      we avoid an infinite loop
      because useEffect doesn't get executed on every render

      React only has 1 thread executing the code
      Flow of execution:
      1st render - so code of Home() is executed
      useEffect is executed
      Encounters setLoading so react now schedules a rerender
      but react's thread is still executing useEffect so it doesn't rerender yet
      when fetch and await are encountered, the thread frees up
      it goes and does the rerender with error as null and loading as true
      */
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

  useEffect(() => 
  {
    if(!user) 
    {
      router.push("/login");
      return;
    }
    fetchPantries();
  }, [user, router]);

  if (!user) 
  {
    // This is for till react finishes first render and then goes and executes useEffect
    return (
      <div className="min-h-screen flex items-center justify-center">
        Loading...
      </div>
    );
  }

  // Show a "Loading..." message while we are fetching pantries
  // This happens on the rerender when loading is set to true and we are awaiting fetch results
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

  const handleCloseModal = () => {
    setModalView('closed');
  }

  const handlePantryAdded = () => {
    handleCloseModal(); //Once pantry is added we want to close the modal
    fetchPantries(); //we want to refresh the pantry list if a new pantry is added
  }

  const handleItemAdded = () => {
    handleCloseModal();
    //Pantries don't need to refresh but the pantry accordion might need to be refreshed
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
            <button 
              onClick={() => setIsSelectionMode(!isSelectionMode)}
              className="px-4 py-2 bg-blue-600 text-white rounded-md shadow hover:bg-blue-700">
              {isSelectionMode? 'Cancel Selection' : 'Select Items for Recipe'}
            </button>

            <button
              onClick={() => setModalView('add')}
              className="px-4 py-2 bg-green-600 text-white rounded-md shadow hover:bg-green-700"
            >
              + Add New...
            </button>
          </div>
          
          {/* Conditional Rendering */}
          {pantries.length === 0 ? (
            <p className="mt-2 text-gray-500">
              You haven't created any pantries yet.
            </p>
          ) : (
            <ul className="space-y-3">
              {/** Map transforms an array into an array of react components
               * pantries.map((pantry) => This line means
               * For each pantry object in the pantries array create the following component:
              */}
              {pantries.map((pantry) => (
                <PantryAccordion 
                  key={pantry.pantryId} 
                  // {/* Below are props for teh pantryAccordion child component */}
                  pantry={pantry}
                  isSelectionMode={isSelectionMode}
                  selectedItemIds={selectedItemIds}
                  /*
                  handleItemSelectToggle functions maintains the state selectedItemIds
                  This is a state that the homepage uses to keep track of all items selected
                  between all the pantries and then passes it to backend
                  So the state needs to be in the homepage component
                  And since we use handleItemSelectToggle to maintain/update this state 
                  we keep handleItemSelectToggle in home too and pass it as a prop
                  */
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
        {modalView !== 'closed' && (
        <div 
          // This is a "backdrop" that covers the screen
          className="fixed inset-0 bg-black bg-opacity-50
                    flex items-center justify-center z-50"
        >
          {/* This is the white pop-up box */}
          <div className="bg-white p-8 rounded-lg shadow-xl max-w-lg w-full relative">
            
            {/* This is the "X" button to close the modal */}
            <button
              onClick={handleCloseModal}
              className="absolute top-2 right-2 text-gray-500 hover:text-gray-900 text-2xl"
            >
              &times; {/* This is an 'X' symbol */}
            </button>
            
            {/*
            * This is the "Conditional Rendering" logic
            * It checks *which* form to show.
            */}
            
            {/* --- View 1: The "Chooser" --- */}
            {modalView === 'add' && (
              <div className="text-center">
                <h2 className="text-2xl font-bold mb-6">What would you like to add?</h2>
                <div className="flex justify-center space-x-4">
                  <button
                    onClick={() => setModalView('addPantry')}
                    className="px-6 py-3 bg-blue-600 text-white rounded-md text-lg"
                  >
                    New Pantry
                  </button>
                  <button
                    onClick={() => setModalView('addItem')}
                    className="px-6 py-3 bg-green-600 text-white rounded-md text-lg"
                  >
                    New Item
                  </button>
                </div>
              </div>
            )}
            
            {/* --- View 2: The "Pantry" Form --- */}
            {modalView === 'addPantry' && (
              <div>
                <h2 className="text-2xl font-bold mb-4">Create New Pantry</h2>
                {/*
                * We render the new component and pass it the "callbacks"
                * it needs to talk back to this parent page.
                */}
                <AddPantryForm
                  onSuccess={handlePantryAdded}
                  onCancel={handleCloseModal}
                />
              </div>
            )}
            
            {/* --- View 3: The "Item" Form --- */}
            {modalView === 'addItem' && (
              <div>
                <h2 className="text-2xl font-bold mb-4">Add Item to Pantry</h2>
                {/*
                * We pass the 'pantries' list (which we already
                * fetched) to this component so it can
                * build the dropdown.
                */}
                <AddItemForm
                  pantries={pantries}
                  onSuccess={handleItemAdded}
                  onCancel={handleCloseModal}
                />
                {/* This is a "helper" link */}
                <button
                  onClick={() => setModalView('addPantry')}
                  className="text-sm text-blue-600 hover:underline mt-4"
                >
                  ...or create a new pantry first
                </button>
              </div>
            )}
          </div>
        </div>
      )}
      {/* --- END OF NEW MODAL BLOCK --- */}
    </main>
  );
}