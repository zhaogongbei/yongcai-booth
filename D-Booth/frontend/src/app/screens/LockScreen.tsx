import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useSettings } from '../stores/useSettings';
import type { Screen } from '../types';
import { GlassCard } from '../components/GlassCard';
import { GlowBtn } from '../components/GlowBtn';

export function LockScreen({ navigate }: { navigate: (s: Screen) => void }) {
  const { settings } = useSettings();
  const [pin, setPin] = useState('');
  const [error, setError] = useState(false);
  const [isUnlocking, setIsUnlocking] = useState(false);
  const [isUnlocked, setIsUnlocked] = useState(false);

  const pinLength = settings.lockScreen?.pinLength || 4;
  const maxPinLength = 6;

  const handleNumberPress = (num: string) => {
    if (pin.length < maxPinLength) {
      setPin(prev => prev + num);
      setError(false);
    }
  };

  const handleDelete = () => {
    setPin(prev => prev.slice(0, -1));
    setError(false);
  };

  const handleClear = () => {
    setPin('');
    setError(false);
  };

  const validatePin = async () => {
    if (pin.length !== pinLength) {
      setError(true);
      return;
    }

    setIsUnlocking(true);

    try {
      // Demo mode: compare with stored pin (in real implementation, call API)
      const storedPin = settings.lockScreen?.pin || '1234'; // Default demo pin

      await new Promise(resolve => setTimeout(resolve, 800));

      if (pin === storedPin) {
        setIsUnlocked(true);
        setTimeout(() => {
          navigate('dashboard');
        }, 1000);
      } else {
        setError(true);
        setPin('');
      }
    } catch (err) {
      setError(true);
      setPin('');
    } finally {
      setIsUnlocking(false);
    }
  };

  useEffect(() => {
    if (pin.length === pinLength) {
      validatePin();
    }
  }, [pin, pinLength]);

  const numberButtons = [
    ['1', '2', '3'],
    ['4', '5', '6'],
    ['7', '8', '9'],
    ['clear', '0', 'delete'],
  ];

  return (
    <div className="w-full h-full flex items-center justify-center relative overflow-hidden">
      {/* Background */}
      {settings.lockScreen?.backgroundImage ? (
        <img
          src={settings.lockScreen.backgroundImage}
          alt="锁屏背景"
          className="absolute inset-0 w-full h-full object-cover"
        />
      ) : (
        <div className="absolute inset-0 bg-gradient-to-br from-blue-900 via-purple-900 to-black" />
      )}

      {/* Overlay */}
      <div className="absolute inset-0 bg-black/40" />

      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="relative z-10 max-w-md w-full px-6"
      >
        <GlassCard className="p-8 backdrop-blur-xl bg-white/10 border-white/20">
          {/* Title */}
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-white mb-2">
              {settings.lockScreen?.title || '拍照亭已锁定'}
            </h1>
            {settings.lockScreen?.subtitle && (
              <p className="text-white/70">{settings.lockScreen.subtitle}</p>
            )}
          </div>

          {/* PIN Display */}
          <div
            className="flex justify-center gap-4 mb-8"
            aria-label={`PIN输入，已输入${pin.length}位，共需要${pinLength}位`}
          >
            {Array.from({ length: pinLength }).map((_, index) => (
              <div
                key={index}
                className={`w-4 h-4 rounded-full transition-all duration-300 ${
                  index < pin.length
                    ? error ? 'bg-red-400 scale-110' : 'bg-white scale-100'
                    : 'bg-white/30 scale-90'
                }`}
              />
            ))}
          </div>

          {/* Error Message */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="text-center text-red-400 mb-4"
                aria-live="assertive"
              >
                PIN码错误，请重试
              </motion.div>
            )}
          </AnimatePresence>

          {/* Numpad */}
          <div className="grid gap-3">
            {numberButtons.map((row, rowIndex) => (
              <div key={rowIndex} className="flex justify-center gap-3">
                {row.map((btn) => (
                  <button
                    key={btn}
                    onClick={() => {
                      if (btn === 'clear') handleClear();
                      else if (btn === 'delete') handleDelete();
                      else handleNumberPress(btn);
                    }}
                    disabled={isUnlocking || isUnlocked}
                    className={`
                      w-16 h-16 rounded-full flex items-center justify-center text-2xl font-medium
                      transition-all duration-200 active:scale-95 focus:outline-none focus:ring-2 focus:ring-blue-400
                      ${btn === 'clear' || btn === 'delete'
                        ? 'bg-white/10 text-white/80 hover:bg-white/20'
                        : 'bg-white/15 text-white hover:bg-white/25'
                      }
                      ${isUnlocking ? 'opacity-50 cursor-not-allowed' : ''}
                    `}
                    aria-label={
                      btn === 'clear' ? '清除PIN码' :
                      btn === 'delete' ? '删除最后一位' :
                      `数字${btn}`
                    }
                  >
                    {btn === 'delete' ? '←' : btn === 'clear' ? 'C' : btn}
                  </button>
                ))}
              </div>
            ))}
          </div>

          {/* Unlock Animation */}
          <AnimatePresence>
            {isUnlocking && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="absolute inset-0 flex items-center justify-center bg-black/50 backdrop-blur-sm rounded-xl"
              >
                <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
              </motion.div>
            )}
          </AnimatePresence>

          <AnimatePresence>
            {isUnlocked && (
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                className="absolute inset-0 flex items-center justify-center bg-green-500/30 backdrop-blur-sm rounded-xl"
              >
                <div className="text-2xl font-bold text-white">解锁成功</div>
              </motion.div>
            )}
          </AnimatePresence>
        </GlassCard>
      </motion.div>
    </div>
  );
};

export default LockScreen;
