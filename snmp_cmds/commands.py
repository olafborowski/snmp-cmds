"""
This internal module serves as an interface between a python application and
the net-snmp binaries on the host system. This module provides a function
for each of the most popular net-snmp binary commands, runs that binary 
with custom options, parse its output, and delivers it back in a meaningful 
form. 
"""

# Standard Library imports
import csv
from subprocess import run, PIPE

# imports for type-hinting purposes
from typing import Union, Optional, List, Tuple, Dict

# Internal module imports
from .exceptions import SNMPTableError, SNMPWriteError
from .helpers import validate_ip_address, check_for_timeout, \
    handle_unknown_error


def snmpget(community: str, ipaddress: str, oid: str,
            port: Union[int, str] = 161, timeout: Union[int, str] = 3) \
        -> Optional[str]:
    """
    Runs Net-SNMP's 'snmpget' command on a given OID, and returns the result.
    :param community: the snmpv2 community string
    :param ipaddress: the IP address of the target SNMP server
    :param oid: the Object IDentifier to request from the target SNMP server
    :param port: the port on which SNMP is running on the target server
    :param timeout: the number of seconds to wait for a response from the 
    SNMP server  
    :return: 
    """
    ipaddress = validate_ip_address(ipaddress)
    host = '{}:{}'.format(ipaddress, port)

    cmdargs = [
        'snmpget', '-Oqv', '-Pe', '-t', str(timeout), '-r', '0', '-v', '2c',
        '-c', community, host, oid]

    cmd = run(cmdargs, stdout=PIPE, stderr=PIPE)

    # Handle any errors that came up
    if cmd.returncode is not 0:
        check_for_timeout(cmd.stderr, host)

        # if previous check didn't generate an Error, this handler will be
        # called as a sort of catch-all
        handle_unknown_error(' '.join(cmdargs), cmd.stderr)
    # Process results
    else:
        # subprocess returns stdout from completed command as a single bytes
        # string. We'll convert it into a regular python string for easier
        # handling
        cmdoutput = cmd.stdout.decode('utf-8')
        # Check for no such instance
        if 'No Such Instance' in cmdoutput:
            return None
        else:
            return cmdoutput


def snmpgetbulk(community: str, ipaddress: str, oids: List[str],
                port: Union[str, int] = 161, timeout: int = 3) \
        -> List[Tuple[str, str]]:
    """
    Runs Net-SNMP's 'snmpget' command on a list of OIDs, and returns a list 
    of tuples of the form (oid, result).
    :param community: the snmpv2 community string
    :param ipaddress: the IP address of the target SNMP server
    :param oids: a list of Object IDentifiers to request from the target 
    SNMP server
    :param port: the port on which SNMP is running on the target server
    :param timeout: the number of seconds to wait for a response from the 
    SNMP server 
    :return: 
    """
    ipaddress = validate_ip_address(ipaddress)
    host = '{}:{}'.format(ipaddress, port)

    if type(oids) is not list:
        oids = [oids]

    cmdargs = [
        'snmpget', '-OQfn', '-Pe', '-t', str(timeout), '-r', '0', '-v', '2c',
        '-c', community, host, *oids
    ]

    cmd = run(cmdargs, stdout=PIPE, stderr=PIPE)

    # Handle any errors that came up
    if cmd.returncode is not 0:
        check_for_timeout(cmd.stderr, host)

        # if previous check didn't generate an Error, this handler will be
        # called as a sort of catch-all
        handle_unknown_error(' '. join(cmdargs), cmd.stderr)
    # Process results
    else:
        cmdoutput = cmd.stdout.splitlines()
        result = []
        for line in cmdoutput:
            # subprocess returns stdout from completed command as a bytes
            # string. We'll convert each line into a regular python string,
            # and separate the OID portion from the result portion
            item = line.decode('utf-8').split(' = ', 1)

            # there is an unfortunate bug / oversight in the net-snmp
            # commands where newline characters within SNMP variables
            # returned from a server are not escaped before printing. if you
            # do an snmpget for 3 oids you'll get 3 lines of output printed (
            # which is what we want), but if one of those 3 variables
            # contains, say, 2 new-line chars in it, you'll get 5 lines of
            # output :(
            # our quick-n-dirty solution is to check each line to see if it
            # "looks" like an oid-value pair (meaning it has a " = " in it). if
            # it doesn't, we'll assume that this line is part of the last pair's
            # value and tack it on accordingly. When we run the .split()
            # function above, if the string did not have a " = " to split on,
            #  the function returns a list with one item: the original string
            if len(item) > 1:  # This is a normal oid-value pair
                # Check for no such instance
                if 'No Such Instance' in item[1]:
                    item[1] = None
                # add it to the results
                result.append(tuple(item))
            else:  # This line is a continuation of the last oid-value pair
                # make a copy of the last oid-value pair for us to edit
                prev_item = list(result[-1])
                # append the new line to it
                prev_item[1] += '\n' + item[0]
                # replace the original with the edited copy
                result[-1] = tuple(prev_item)

        return result


def snmpwalk(community: str, ipaddress: str, oid: str,
             port: Union[str, int] = 161, timeout: int = 3) \
        -> List[Tuple[str, str]]:
    """
    Runs Net-SNMP's 'snmpget' command on a list of OIDs, and returns a list 
    of tuples of the form (oid, result).
    :param community: the snmpv2 community string
    :param ipaddress: the IP address of the target SNMP server
    :param oid: the Object IDentifier to request from the target SNMP server
    :param port: the port on which SNMP is running on the target server
    :param timeout: the number of seconds to wait for a response from the 
    SNMP server 
    :return: 
    """
    ipaddress = validate_ip_address(ipaddress)
    host = '{}:{}'.format(ipaddress, port)

    cmdargs = [
        'snmpwalk', '-OQfn', '-Pe', '-t', str(timeout), '-r', '0', '-v', '2c',
        '-c', community, host, oid
    ]

    cmd = run(cmdargs, stdout=PIPE, stderr=PIPE)

    # Handle any errors that came up
    if cmd.returncode is not 0:
        check_for_timeout(cmd.stderr, host)

        # if previous check didn't generate an Error, this handler will be
        # called as a sort of catch-all
        handle_unknown_error(' '.join(cmdargs), cmd.stderr)
    # Process results
    else:
        cmdoutput = cmd.stdout.splitlines()
        result = []
        for line in cmdoutput:
            # subprocess returns stdout from completed command as a bytes
            # string. We'll convert each line into a regular python string,
            # and separate the OID portion from the result portion
            item = line.decode('utf-8').split(' = ', 1)

            # there is an unfortunate bug / oversight in the net-snmp
            # commands where newline characters within SNMP variables
            # returned from a server are not escaped before printing. if you
            # do an snmpget for 3 oids you'll get 3 lines of output printed (
            # which is what we want), but if one of those 3 variables
            # contains, say, 2 new-line chars in it, you'll get 5 lines of
            # output :(
            # our quick-n-dirty solution is to check each line to see if it
            # "looks" like an oid-value pair (meaning it has a " = " in it). if
            # it doesn't, we'll assume that this line is part of the last pair's
            # value and tack it on accordingly. When we run the .split()
            # function above, if the string did not have a " = " to split on,
            #  the function returns a list with one item: the original string
            if len(item) > 1:  # This is a normal oid-value pair
                # Check for no such instance
                if 'No Such Instance' in item[1]:
                    item[1] = None
                # add it to the results
                result.append(tuple(item))
            else:  # This line is a continuation of the last oid-value pair
                # make a copy of the last oid-value pair for us to edit
                prev_item = list(result[-1])
                # append the new line to it
                prev_item[1] += '\n' + item[0]
                # replace the original with the edited copy
                result[-1] = tuple(prev_item)

        return result


def snmptable(community: str, ipaddress: str, oid: str,
              port: Union[str, int] = 161, timeout: int = 3,
              sortkey: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Runs Net-SNMP's 'snmptable' command on a given OID, converts the results
    into a list of dictionaries, and optionally sorts the list by a given key.
    :param community: the snmpv2 community string
    :param ipaddress: the IP address of the target SNMP server
    :param oid: the Object IDentifier to request from the target SNMP server
    :param port: the port on which SNMP is running on the target server
    :param sortkey: the key within each dict upon which to sort the list of 
    results
    :param timeout: the number of seconds to wait for a response from the 
    SNMP server
    :return: a list of dicts, one for each row of the table. The keys of the 
    dicts correspond to the column names of the table.
    """

    # We want our delimiter to be something that would never show up in the
    # wild, so we'll use the non-printable ascii character RS (Record Separator)
    delimiter = '\x1E'

    ipaddress = validate_ip_address(ipaddress)
    host = '{}:{}'.format(ipaddress, port)

    cmdargs = [
        'snmptable', '-m', 'ALL', '-Pe', '-t', str(timeout), '-r', '0', '-v',
        '2c', '-Cif', delimiter, '-c', community, host, oid
    ]

    cmd = run(cmdargs, stdout=PIPE, stderr=PIPE)

    # Handle any errors that came up
    if cmd.returncode is not 0:
        check_for_timeout(cmd.stderr, host)

        if b'Was that a table?' in cmd.stderr:
            raise SNMPTableError(oid)
        else:
            handle_unknown_error(' '.join(cmdargs), cmd.stderr)
    # Process results
    else:
        # subprocess returns stdout from completed command as a single bytes
        # string. we'll split it into a list of bytes strings, and convert
        # each into a standard python string which the csv reader can handle
        cmdoutput = cmd.stdout.splitlines()
        cmdoutput = [item.decode('utf-8') for item in cmdoutput]

        # Strip the table name and the blank line following it from the output,
        # so all that remains is the table itself
        cmdoutput = cmdoutput[2:]
        table_parser = csv.DictReader(cmdoutput, delimiter=delimiter)
        results = [element for element in table_parser]
        if sortkey:
            results.sort(key=lambda i: i[sortkey])
        return results


def snmpset(community: str, ipaddress: str, oid: str, type: str, value: str,
            port: Union[int, str] = 161, timeout: Union[int, str] = 3) \
        -> Optional[str]:
    """
    Runs Net-SNMP's 'snmpget' command on a given OID, and returns the result.
    :param community: the snmpv2 community string
    :param ipaddress: the IP address of the target SNMP server
    :param oid: the Object IDentifier to request from the target SNMP server
    :param port: the port on which SNMP is running on the target server
    :param timeout: the number of seconds to wait for a response from the 
    SNMP server  
    :return: 
    """
    ipaddress = validate_ip_address(ipaddress)
    host = '{}:{}'.format(ipaddress, port)

    # snmpset type checking
    valid_types = ['i', 'u', 't', 'a', 'o', 's', 'x', 'd', 'b']
    for type_code in valid_types:
        if type == type_code:
            # the type argument is one of snmpset's accepted type codes
            break
    else:
        # type didn't match any type code accepted by snmpset
        raise SNMPWriteError(
            "The type value you specified does not match one of the accepted "
            "type codes.\nValid type codes are one of ({})"
                .format("|".join(valid_types))
        )

    cmdargs = [
        'snmpset', '-OQfn', '-t', str(timeout), '-r', '0', '-v', '2c', '-c',
        community, host, oid, type, value]

    cmd = run(cmdargs, stdout=PIPE, stderr=PIPE)

    # Handle any errors that came up
    if cmd.returncode is not 0:
        check_for_timeout(cmd.stderr, host)

        # Check for write errors
        for errormsg in [b'Bad variable type', b'Value out of range']:
            if errormsg in cmd.stderr:
                raise SNMPWriteError(cmd.stderr)

        # if previous check didn't generate an Error, this handler will be
        # called as a sort of catch-all
        handle_unknown_error(' '.join(cmdargs), cmd.stderr)
    # Process results
    else:
        # subprocess returns stdout from completed command as a single bytes
        # string. We'll convert it into a regular python string for easier
        # handling
        cmdoutput = cmd.stdout.decode('utf-8')
        # Check for no such instance
        if 'No Such Instance' in cmdoutput:
            raise SNMPWriteError(
                "We've received a 'No Such Instance' error from the server. "
                "This can be caused by a number of things. Most likely, your "
                "SNMP write community is incorrect, the OID you specified "
                "doesn't exist on your target device, or your target device "
                "doesn't support writing to this writeable field")
        else:
            return cmdoutput