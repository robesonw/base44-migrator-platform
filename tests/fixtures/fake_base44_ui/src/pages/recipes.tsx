import { useEffect, useState } from 'react';

const NEXT_PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000/api';

export default function RecipesPage() {
  const [recipes, setRecipes] = useState([]);

  useEffect(() => {
    // Fetch with literal string
    fetch(`${NEXT_PUBLIC_API_URL}/recipes`)
      .then(res => res.json())
      .then(data => setRecipes(data));
    
    // Fetch with template string (dynamic)
    const recipeId = '123';
    fetch(`${NEXT_PUBLIC_API_URL}/recipes/${recipeId}`)
      .then(res => res.json())
      .then(data => console.log(data));
  }, []);

  const createRecipe = async (recipeData: any) => {
    // POST with body
    const response = await fetch(`${NEXT_PUBLIC_API_URL}/recipes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(recipeData)
    });
    return response.json();
  };

  return <div>Recipes</div>;
}


