import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';

export default function AdminFeedback() {
  const { data: feedbacks = [], isLoading } = useQuery({
    queryKey: ['feedbacks'],
    queryFn: fetchFeedbacks,
  });

  if (isLoading) return <div>Loading...</div>;

  return (
    <div>
      {feedbacks.map(feedback => ( <p key={feedback.id}>{feedback.message}</p> ))}
    </div>
  );
}

async function fetchFeedbacks() {
  const response = await fetch('/api/feedbacks');
  return response.json();
}