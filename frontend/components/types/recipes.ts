export interface Ingredient {
    pantryItemId: number;
    ingredientName: string;
    quantity: number;
    unit: string;
}

export interface Recipe {
    description: string;
    ingredients: Ingredient[];
    steps: string[];
    timeRequired: string;
}

export interface RecipeSuggestions {
    recipes: Recipe[];
}

export interface ProactiveMealDisplayData {
    breakfast?: RecipeSuggestions | null;
    lunch?: RecipeSuggestions | null;
    eveningSnack?: RecipeSuggestions | null;
    dinner?: RecipeSuggestions | null;
}