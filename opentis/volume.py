'''
Created on 03.09.2014

@author: jan-hendrikprinz
'''

class Volume(object):
    def __init__(self):
        '''
        A Volume describes a set in configuration space
        '''
        pass
    
    def __call__(self, snapshot):
        '''
        Returns `True` if the given snapshot is part of the defined Region
        '''
        
        return False
                
    def __str__(self):
        '''
        Returns a string representation of the volume
        '''
        return 'volume'

    def __or__(self, other):
        if self is other:
            return self
        elif type(self) is EmptyVolume:
            return other
        elif type(other) is EmptyVolume:
            return self
        elif type(self) is FullVolume:
            return self
        elif type(other) is FullVolume:
            return other
        else:
            return VolumeCombination(self, other, fnc = lambda a,b : a or b, str_fnc = '{0} or {1}')

    def __xor__(self, other):
        if self is other:
            return EmptyVolume()
        elif type(self) is EmptyVolume:
            return other
        elif type(other) is EmptyVolume:
            return self
        elif type(self) is FullVolume:
            return NegatedVolume(other)
        elif type(other) is FullVolume:
            return NegatedVolume(self)
        else:
            return VolumeCombination(self, other, fnc = lambda a,b : a ^ b, str_fnc = '{0} xor {1}')

    def __and__(self, other):
        if self is other:
            return self
        elif type(self) is EmptyVolume:
            return self
        elif type(other) is EmptyVolume:
            return other
        elif type(self) is FullVolume:
            return other
        elif type(other) is FullVolume:
            return self
        else:
            return VolumeCombination(self, other, fnc = lambda a,b : a and b, str_fnc = '{0} and {1}')

    def __sub__(self, other):
        if self is other:
            return EmptyVolume()
        elif type(self) is EmptyVolume:
            return self
        elif type(other) is EmptyVolume:
            return self
        elif type(self) is FullVolume:
            return NegatedVolume(other)
        elif type(other) is FullVolume:
            return EmptyVolume()        
        else:
            return VolumeCombination(self, other, fnc = lambda a,b : a and not b, str_fnc = '{0} and not {1}')
        
    def __invert__(self):
        if type(self) is EmptyVolume:
            return FullVolume()
        elif type(self) is FullVolume:
            return EmptyVolume(self)
        else:
            return NegatedVolume(self)

    
class VolumeCombination(Volume):
    def __init__(self, volume1, volume2, fnc, str_fnc):
        super(VolumeCombination, self).__init__()
        self.volume1 = volume1
        self.volume2 = volume2
        self.fnc = fnc
        self.sfnc = str_fnc

    def __call__(self, snapshot):
        return self.fnc(self.volume1.__call__(snapshot), self.volume2.__call__(snapshot))
    
    def __str__(self):
        return '(' + self.sfnc.format(str(self.volume1), str(self.volume2)) + ')'
    
class NegatedVolume(Volume):
    def __init__(self, volume):
        super(NegatedVolume, self).__init__()
        self.volume = volume

    def __call__(self, snapshot):
        return not self.volume(snapshot)
    
    def __str__(self):
        return '(not ' + str(self.volume) + ')'
    
    
class EmptyVolume(Volume):
    def __init__(self):
        super(EmptyVolume, self).__init__()

    def __call__(self, snapshot):
        return False
    
    def __str__(self):
        return 'empty'
    
class FullVolume(Volume):
    def __init__(self):
        super(FullVolume, self).__init__()

    def __call__(self, snapshot):
        return True
    
    def __str__(self):
        return 'all'

class LambdaVolume(Volume):
    '''
    Defines a Volume containing all states where orderparameter is in a given range.
    '''
    def __init__(self, orderparameter, lambda_min = 0.0, lambda_max = 1.0):
        '''
        Attributes
        ----------
        orderparameter : orderparameter
            the orderparameter object
        lambda_min : float
            the minimal allowed orderparameter
        lambda_max: float
            the maximal allowed orderparameter
        '''
        super(LambdaVolume, self).__init__()
        self.orderparameter = orderparameter
        self.lambda_min = lambda_min
        self.lambda_max = lambda_max
        
    def __call__(self, snapshot):
        l = self.orderparameter(snapshot)
        return l >= self.lambda_min and l <= self.lambda_max

    def __str__(self):
        return '{{x|{2}(x) in [{0}, {1}]}}'.format( self.lambda_min, self.lambda_max, self.orderparameter.name)

class LambdaVolumePeriodic(LambdaVolume):
    """
    Defines a Volume containing all states where orderparameter, a periodic
    function wrapping into the range [period_min, period_max], is in the
    given range [lambda_min, lambda_max].

    """
    def __init__(self, orderparameter, lambda_min = 0.0, lambda_max = 1.0,
                                       period_min = None, period_max = None):
        """
        Attributes
        ----------
        period_min : float (optional)
            minimum of the periodic domain
        period_max : float (optional)
            maximum of the periodic domain
        """
        super(LambdaVolumePeriodic, self).__init__(orderparameter,
                                                    lambda_min, lambda_max)        
        if (period_min is not None) and (period_max is not None):
            self.period_shift = period_min
            self.period_len = period_max - period_min
            if self.lambda_max - self.lambda_min > self.period_len:
                raise Exception("Range of volume larger than periodic bounds.")
            elif self.lambda_max-self.lambda_min == self.period_len:
                self.lambda_min = period_min
                self.lambda_max = period_max
            else:
                self.lambda_min = self.do_wrap(lambda_min)
                self.lambda_max = self.do_wrap(lambda_max)
            self.wrap = True
        else:
            self.wrap = False

    def do_wrap(self, value):
        return ((value-self.period_shift) % self.period_len) + self.period_shift
        
    def __call__(self, snapshot):
        l = self.orderparameter(snapshot)
        if self.wrap:
            l = self.do_wrap(l)
        if self.lambda_min > self.lambda_max:
            return l >= self.lambda_min or l <= self.lambda_max
        else:
            return l >= self.lambda_min and l <= self.lambda_max

    def __str__(self):
        if self.wrap:
            fcn = 'x|({0}(x) - {2}) % {1} + {2}'.format(
                        self.orderparameter.name,
                        self.period_len, self.period_shift)
            if self.lambda_min < self.lambda_max:
                domain = '[{0}, {1}]'.format(
                        self.lambda_min, self.lambda_max)
            else:
                domain = '[{0}, {1}] union [{2}, {3}]'.format(
                        self.period_shift, self.lambda_max,
                        self.lambda_min, self.period_shift+self.period_len)
            return '{'+fcn+' in '+domain+'}'
        else:
            return '{{x|{2}(x) [periodic] in [{0}, {1}]}}'.format( 
                        self.lambda_min, self.lambda_max, 
                        self.orderparameter.name)

    
class VoronoiVolume(Volume):
    '''
    Defines a Volume that is given by a Voronoi cell specified by a set of centers
    
    Parameters
    ----------
    orderparameter : OP_Multi_RMSD
        must be an OP_Multi_RMSD orderparameter that returns several RMSDs
    state : int
        the index of the center for the chosen voronoi cell

    Attributes
    ----------
    orderparameter : orderparameter
        the orderparameter object
    state : int
        the index of the center for the chosen voronoi cell

    '''
    
    def __init__(self, orderparameter, state):
        super(VoronoiVolume, self).__init__()
        self.orderparameter = orderparameter
        self.state = state
        
    def cell(self, snapshot):
        '''
        Returns the index of the voronoicell snapshot is in
        
        Parameters
        ----------
        snapshot : Snapshot
            the snapshot to be tested
        
        Returns
        -------
        int
            index of the voronoi cell
        '''
        distances = self.orderparameter(snapshot)
        min_val = 1000000000.0
        min_idx = -1 
        for idx, d in enumerate(distances):
            if d < min_val:
                min_val = d
                min_idx = idx
        
        return min_idx

    def __call__(self, snapshot, state = None):
        '''
        Returns `True` if snapshot belongs to voronoi cell in state
        
        Parameters
        ----------
        snapshot : Snapshot
            snapshot to be tested
        state : int or None
            index of the cell to be tested. If `None` (Default) then the internal self.state is used
            
        Returns
        -------
        bool
            returns `True` is snapshot is on the specified voronoi cell
        
        '''
        
        # short but slower would be 
        
        if state is None:
            state = self.state
        
        return self.cell(snapshot) == state

class VolumeFactory(object):
    @staticmethod
    def _check_minmax(minvals, maxvals):
        # minvals could be an integer
        if len(minvals) != len(maxvals):
            raise ValueError(
                "len(minvals) != len(maxvals) in LambdaVolumePeriodicSet")
        return (minvals, maxvals)

    @staticmethod
    def LambdaVolumeSet(op, minvals, maxvals):

        minvals, maxvals = VolumeFactory._check_minmax(minvals, maxvals)
        myset = []
        for i in range(len(maxvals)):
            myset.append(LambdaVolume(op, minvals[i], maxvals[i]))
        return myset

    @staticmethod
    def LambdaVolumePeriodicSet(op, minvals, maxvals, 
                                period_min=None, period_max=None):
        minvals, maxvals = VolumeFactory._check_minmax(minvals, maxvals)
        myset = []
        for i in range(len(maxvals)):
            myset.append(LambdaVolumePeriodic(op, minvals[i], maxvals[i], 
                                              period_min, period_max))
        return myset