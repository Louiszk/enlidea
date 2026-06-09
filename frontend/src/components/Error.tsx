import React from 'react';
import { SadFace } from './Icons';

const Error = ({ message = 'Something went wrong. Please try again later.' }) => {
    return (
        <div className='flex flex-col gap-8 justify-center items-center text-center p-4'>
            <p className='text-red-300 font-bold'>{message}</p>
            <SadFace />
        </div>
    );
};

export default Error;