import React from 'react';
import PersonalInformation from './PersonalInformation';
import AccountDeletion from './AccountDeletion';

const AccountSettings = () => {
  return (
    <div className="space-y-8 mt-8 mx-4 w-full">
      <PersonalInformation />
      <AccountDeletion />
    </div>
  );
};

export default AccountSettings;
