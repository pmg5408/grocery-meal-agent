"use client";

import React, { useState } from "react";

interface Ingredient {
    pantryItemId: number;
    ingredientName: string;
    quantity: number;
    unit: string;
}

interface Recipe {
    description: string;
    ingredients: Ingredient[];
    steps: string[];
    timeRequired: string;
}

interface ProactiveMealDisplayProps {
    proactiveMeals: {
        breakfast?: Recipe[];
        lunch?: Recipe[];
        eveningSnack?: Recipe[];
        dinner?: Recipe[];
    };
    onMealConfirmed: () => void; // parent (page.tsx) refreshes pantry + clears suggestion if needed
}

export default function ProactiveMealDisplay({proactiveMeals, onMealConfirmed}: ProactiveMealDisplayProps)
{
    const [selectedRecipe, setSelectedRecipe] = useState<Recipe | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null)

    const handleConfirmedMeal = async (event: React.FormEvent) => 
    {
        event.preventDefault();
        if(!selectedRecipe) return;

        try
        {
            setLoading(true);
            setError(null);

            const response = await fetch 
            (
                'http://127.0.0.1:8000/selectedMeal',
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
                throw new Error("Meal submission failed");
            }
            
        }
        catch(err:any)
        {
            setError(err.message);
        }
        finally
        {
            setLoading(false);
        }
        setSelectedRecipe(null);
        onMealConfirmed();
    }
    const renderWindow = (title: string, recipes?: Recipe[]) => {
        if (!recipes || recipes.length === 0) return null;

        return (
            <div className="mt-6 p-4 bg-white shadow rounded-lg">
                <h2 className="text-xl font-semibold text-blue-700 mb-3">{title}</h2>

                <div className="space-y-3">
                    {recipes.map((recipe, idx) => (
                        <button
                            key={idx}
                            className={`w-full p-4 rounded-lg text-left border-2 transition-all ${
                                selectedRecipe === recipe
                                    ? "border-green-600 bg-green-50"
                                    : "border-gray-200 hover:bg-gray-100"
                            }`}
                            onClick={() => setSelectedRecipe(recipe)}
                        >
                            <h4 className="font-semibold text-lg text-black">
                                {recipe.description}
                            </h4>

                            {selectedRecipe === recipe && (
                                <div className="mt-4 border-t border-black pt-4">
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
            </div>
        );
    };

    return (
        <div className="mt-10">
            <h1 className="text-2xl font-bold text-black mb-4">Proactive Meal Suggestions</h1>

            {renderWindow("Breakfast", proactiveMeals.breakfast)}
            {renderWindow("Lunch", proactiveMeals.lunch)}
            {renderWindow("Evening Snack", proactiveMeals.eveningSnack)}
            {renderWindow("Dinner", proactiveMeals.dinner)}

            {selectedRecipe && (
                <div className="mt-6">
                    {error && <p className="text-red-600 mb-2">{error}</p>}

                    <button
                        onClick={handleConfirmedMeal}
                        disabled={loading}
                        className={`w-full py-2 px-4 rounded-md text-white ${
                            loading ? "bg-gray-400" : "bg-green-600 hover:bg-green-700"
                        }`}
                    >
                        {loading
                            ? "Confirming..."
                            : `Confirm & Cook "${selectedRecipe.description}"`}
                    </button>
                </div>
            )}
        </div>
    );
}