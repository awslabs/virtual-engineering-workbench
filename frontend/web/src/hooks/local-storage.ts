import { useEffect, useState, SetStateAction, Dispatch } from 'react';

/* eslint no-undef: "off" */

const useLocalStorage = (storageKey: string, defaultValue: string | null = null):
[string | null, Dispatch<SetStateAction<string | null>>] => {
  const [value, setValue] = useState<string | null>(
    localStorage.getItem(storageKey) ?? defaultValue
  );

  useEffect(() => {
    if (!value) {
      localStorage.removeItem(storageKey);
    } else {
      localStorage.setItem(storageKey, value);
    }
  }, [value, storageKey]);

  return [value, setValue];
};

const useLocalStorageNumber = (storageKey: string, defaultValue?: number):
[number | undefined, Dispatch<SetStateAction<number | undefined>>] => {
  const [value, setValue] = useState<number | undefined>(
    Number(localStorage.getItem(storageKey) ?? defaultValue)
  );

  useEffect(() => {
    if (!value) {
      localStorage.removeItem(storageKey);
    } else {
      localStorage.setItem(storageKey, value.toString());
    }
  }, [value, storageKey]);

  return [value, setValue];
};


const useLocalStorageDate = (storageKey: string, defaultValue: Date | null = null):
[Date | null, Dispatch<SetStateAction<Date | null>>] => {
  function getValidDate(unsafeDateValue: string | null) {
    if (unsafeDateValue) {
      const d = new Date(unsafeDateValue);
      return d instanceof Date && !isNaN(Number(d)) ? d : null;
    }
    return null;

  }
  const [value, setValue] = useState<Date | null>(
    getValidDate(localStorage.getItem(storageKey)) ?? defaultValue
  );

  useEffect(() => {
    if (!value) {
      localStorage.removeItem(storageKey);
    } else {
      localStorage.setItem(storageKey, value.toISOString());
    }
  }, [value, storageKey]);

  return [value, setValue];
};

export { useLocalStorage, useLocalStorageNumber, useLocalStorageDate };