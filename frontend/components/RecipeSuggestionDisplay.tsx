"use client";

import React, {useState} from 'react';

interface Ingredient
{
    pantryItemId: number,
    ingredientName: string,
    quantity: number,
    unit: string
}

interface Recipe
{
    description: string,
    ingredients: Ingredient[],
    steps: string[],
    timeRequired: string
}

interface Result
{
    recipes: Recipe[]
}

interface RecipeSuggestionDisplayProps
{
    suggestionData: Result,
    onMealConfirmed: () => void,
}

export default function RecipeSuggestionDisplay({suggestionData, onMealConfirmed}: RecipeSuggestionDisplayProps) 
{
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    const [selectedRecipe, setSelectedRecipe] = useState<Recipe | null>(null);

    const handleRecipeSelection = async (recipe: Recipe) => 
    {
        if(recipe == selectedRecipe)
        {
            setSelectedRecipe(null);
        }
        else
        {     
            setSelectedRecipe(recipe);
        }
    }

    const handleRecipeSubmission = async (event: React.FormEvent) => 
    {
        event.preventDefault();

        setLoading(true);
        setError(null);

        try
        {
          const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;
          const response = await fetch
          (
              `http://${API_BASE_URL}/selectedMeal`,
              {
                  method: 'POST',
                  headers: 
                  {
                    'Authorization': `Bearer ${localStorage.getItem("jwt")}`,
                    'Content-Type': 'application/json'
                  },
                  body: JSON.stringify(selectedRecipe?.ingredients)
              }
          )
          if(!response.ok)
          {
              throw new Error('Encountered an error while trying to submit the recipe selection')
          }
        }
        catch(err: any)
        {
            setError(err.message);
        }
        finally
        {
            setLoading(false);
        }

        setSelectedRecipe(null);
        //Maybe want to call 1 function from here in home and from there set suggestion to null and call fetch pantries
        onMealConfirmed();
    }

    return (
        <div className="mt-8 p-6 bg-white shadow rounded-lg">

            <p className="text-sm text-black">Select a meal to see details and confirm.</p>
            
            {/* --- 2. The List of Recipes --- */}
            <div className="mt-4 space-y-3">
              {/*
               * We "map" (loop) over the 'suggestionResult.recipes'
               * which was passed in as a "prop" from 'page.tsx'.
               */}
              {suggestionData.recipes.map((recipe: Recipe, index: number) => (
                
                // We make each recipe a *clickable button*
                <button
                  key={index}
                  // When clicked, it calls your new "selection" function
                  onClick={() => handleRecipeSelection(recipe)}
                  
                  // This "highlights" the button if it's
                  // the one in our 'selectedRecipe' state.
                  className={`w-full p-4 rounded-lg text-left
                              border-2 transition-all
                              ${selectedRecipe === recipe 
                                ? 'border-blue-600 bg-blue-50' 
                                : 'border-gray-200 hover:bg-gray-50'
                              }`}
                >
                  <h4 className="font-semibold text-lg text-black">{recipe.description}</h4>
                  
                  {/* This "details" view *only* appears
                       if this recipe is the selected one */}
                  {selectedRecipe === recipe && (
                    <div className="mt-4 pt-4 border-t border-black">
                      <h5 className="font-semibold text-black">Ingredients:</h5>
                      <ul className="list-disc list-inside text-sm text-black">
                        {recipe.ingredients.map((ing, i) => (
                          <li key={i}>
                            {ing.quantity} {ing.unit} {ing.ingredientName}
                          </li>
                        ))}
                      </ul>
                      <h5 className="font-semibold mt-2 text-black">Steps:</h5>
                      <ol className="list-decimal list-inside text-sm text-black">
                        {recipe.steps.map((step, i) => (
                           <li key={i}>{step}</li>
                        ))}
                      </ol>
                    </div>
                  )}
                </button>
              ))}
            </div>

            {/* --- 3. The "Confirm" Button --- */}
            {/* This whole section *only* appears if
                 a recipe has been selected. */}
            {selectedRecipe && (
              <form onSubmit={handleRecipeSubmission} className="mt-6">
                
                {error && (
                  <p className="text-sm text-red-600 mb-2">{error}</p>
                )}
                
                <button
                  type="submit"
                  disabled={loading || !selectedRecipe}
                  className="w-full py-2 px-4 bg-green-600 text-white rounded-md
                             disabled:bg-gray-400 hover:bg-green-700"
                >
                  {loading 
                    ? 'Deducting Ingredients...' 
                    : `Confirm & Cook "${selectedRecipe.description}"`
                  }
                </button>
              </form>
            )}
        </div>
    );
};