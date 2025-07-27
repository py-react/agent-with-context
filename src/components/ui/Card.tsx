import React from 'react';

interface CardProps {
  className?: string;
  children: React.ReactNode;
}

export const Card: React.FC<CardProps> = ({
  className = '',
  children
}) => {
  const baseClasses = 'rounded-lg border border-gray-200 bg-white shadow-sm';

  return (
    <div className={`${baseClasses} ${className}`}>
      {children}
    </div>
  );
}; 