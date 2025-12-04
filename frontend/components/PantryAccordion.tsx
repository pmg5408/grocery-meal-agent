"use client";

import {useState} from 'react';

interface Item{
    itemId: number,
    itemName: string | null,
    brand: string | null,
    avgShelfLife: string | null,
};

interface PantryItem{
    id: number,
    pantryId: number,
    itemId: number,
    quantity: number,
    unit: string | null,
    purchaseDate: string,
    item: Item
};

interface Pantry{
    pantryId: number,
    pantryNickname: string,
    userId: number
};

interface PantryAccordionProps{
    pantry: Pantry,
    isSelectionMode: boolean,
    selectedItemIds: Set<number>,
    onItemSelectToggle: (pantryItemId: number) => void;
};

export default function PantryAccordion ({ 
    pantry,
    isSelectionMode,
    selectedItemIds,
    onItemSelectToggle,
 }: PantryAccordionProps) 
{

    const [items, setItems] = useState<PantryItem[]>([]);
    const [isExpanded, setIsExpanded] = useState(false);

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handlePantryExpand = async () => 
    {
    /*
        Executed every time arrow is clicked
        but nothing is executed in the function when the pantry is already expanded
    */
        setIsExpanded(!isExpanded);

        if(!isExpanded)
        {
            try
            {
                setLoading(true);
                setError(null);

                const response = await fetch(
                    `http://127.0.0.1:8000/${pantry.pantryId}/items`,
                    {
                      headers:
                      {
                        'Authorization': `Bearer ${localStorage.getItem("jwt")}`,
                      }
                    }
                );

                if(!response.ok){
                    throw new Error("failed to get items for this pantry");
                }

                const pantryItems: PantryItem[] = await response.json();
                setItems(pantryItems);
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
    };

    return (
        <li className="bg-white rounded-lg shadow">
          {/* --- This is the "Button" part of the accordion --- */}
          <button
            onClick={handlePantryExpand}
            className="w-full flex justify-between items-center p-4"
          >
            <span className="text-xl font-medium text-blue-700">
              {pantry.pantryNickname}
            </span>
            {/* This is a "downward arrow" icon that rotates */}
            <svg
              className={`w-5 h-5 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </button>
    
          {/* * --- This is the "Expandable" part ---
           * "Conditional Rendering": This 'div' and
           * everything inside it will *only* be rendered
           * if 'isExpanded' is true.
           */}
          {isExpanded && (
            <div className="p-4 border-t border-gray-200">
              {/* This component handles its *own* loading/error */}
              {loading && <p>Loading items...</p>}
              {error && <p className="text-red-600">Error: {error}</p>}
              
              {/* * --- The "Happy Path" (Loaded, no error) ---
               * We check if we *are not* loading AND
               * if the 'items' list is empty.
               */}
              {!loading && items.length === 0 && (
                <p className="text-black">This pantry is empty.</p>
              )}
    
              {/* * If we are *not* loading AND we *have* items
               */}
              {!loading && items.length > 0 && (
                <ul className="space-y-2">
                  {/* We "map" over this component's 'items' state */}
                  {items.map((pantryItem) => (
                    <li 
                      key={pantryItem.id} 
                      className="flex justify-between items-center p-2 bg-gray-50 rounded"
                    >
                    {/* --- ADD THIS ENTIRE NEW BLOCK ---
                    * This is the "checkbox" you wanted.
                    * It is "conditionally rendered" and will *only*
                    * appear if 'isSelectionMode' is true.
                   */}
                    {isSelectionMode && (
                        <input
                            type="checkbox"
                            className="h-5 w-5 mr-3"
                        
                            // This reads the "parent's" state to
                            // know if it should be checked.
                            checked={selectedItemIds.has(pantryItem.id)}
                        
                            // When clicked, this calls the "parent's"
                            // function to update the list.
                            onChange={() => onItemSelectToggle(pantryItem.id)}
                        />
                    )}
                    {/*--- UPDATE THIS WRAPPER DIV ---
                    * We add 'flex-grow' so it takes up the rest
                    * of the space next to the checkbox.
                   */}
                    <div className="flex-grow flex justify-between items-center"></div>
                      <div>
                        {/* * We use the "nested" item data
                         * 'pantryItem.item.itemName'
                         */}
                        <span className="font-semibold text-black">
                          {pantryItem.item.itemName || 'Unknown Item'}
                        </span>
                        <span className="text-sm text-gray-600 ml-2">
                          ({pantryItem.item.brand || 'N/A'})
                        </span>
                      </div>
                      <div>
                        <span className="text-sm text-gray-800 mr-4">
                          Qty: {pantryItem.quantity} {pantryItem.unit || ''}

                        </span>
                        <span className="text-sm text-gray-500">
                          {/* * We format the JSON date string
                           * to be more readable
                           */}
                          Added: {new Date(pantryItem.purchaseDate).toLocaleDateString()}
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </li>
    );
}