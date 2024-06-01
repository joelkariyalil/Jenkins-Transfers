"""

Summary - Code that Transfers Job b/w Jenkins Servers without requiring a server restart.
Created by - Joel Thomas Chacko
Created On - 12-03-2024

"""

import jenkins
import os
from lxml import etree
import argparse
import json


def establish_connection_to_servers(production_url, interim_url, production_username, interim_username, production_password, interim_password):
    """
    Establishes connection to servers using the provided production and interim URLs, username, and password.

    Parameters:
    - production_url (str): The URL for the production server.
    - interim_url (str): The URL for the interim server.
    - username (str): The username for authentication.
    - password (str): The password for authentication.

    Returns:
    - production_server (jenkins.Jenkins): Connection to the production server.
    - interim_server (jenkins.Jenkins): Connection to the interim server.
    """
    try:
        production_server = jenkins.Jenkins(production_url, username=production_username, password=production_password)
        interim_server = jenkins.Jenkins(interim_url, username=interim_username, password=interim_password)
        return production_server, interim_server
    except Exception as e:
        print('Exception in Establishing Connection: ', e)


def get_config_xml(conn, job_name):
    """
    Retrieve the configuration XML for a specific job from the Jenkins server.

    :param conn: Jenkins server connection object
    :param job_name: Name of the job to retrieve the configuration XML for
    :return: The configuration XML of the specified job, or None if an exception occurs
    """
    try:
        config_xml = conn.get_job_config(job_name)
    except jenkins.JenkinsException:
        config_xml = None
    return config_xml


def create_job(production_conn, job_name, config_xml):
    """
    Creates a job on Jenkins-Production using the provided connection, job name, and configuration XML.

    Parameters:
    - production_conn: the connection to Jenkins-Production
    - job_name: the name of the job to be created
    - config_xml: the XML configuration for the job

    Returns:
    None
    """
    try:
        production_conn.create_job(job_name, config_xml)
        print(f"CREATED on Jenkins-Production JOB - {production_url}\t\t->\t{job_name}")
    except jenkins.JenkinsException as e:
        print(f"FAILED to Create Job. Error: {e}")


def update_job(production_conn, job_name, config_xml):
    """
    A function to update a job on Jenkins-Production with the provided configuration XML.

    Parameters:
    - production_conn: the connection to the Jenkins-Production server
    - job_name: the name of the job to be updated
    - config_xml: the new configuration XML for the job

    Returns:
    None
    """
    try:
        production_conn.reconfig_job(job_name, config_xml)
        print(f"UPDATED on Jenkins-Production JOB - {production_url}\t\t->\t{job_name}")
    except jenkins.JenkinsException as e:
        print(f"FAILED to Create Job. Error: {e}")


def create_view(production_conn, view_name, config_xml):
    """
        A function to create a specified view in Jenkins production environment.

        Args:
            production_conn: Connection to the Jenkins production environment.
            view_name: Name of the view to be updated.
            config_xml: Configuration XML for the updated view.

        Returns:
            None
    """
    try:
        production_conn.create_view(view_name, config_xml)
        print(f"CREATED on Jenkins-Production VIEW - {production_url}\t\t->\t{view_name}")
    except jenkins.JenkinsException as e:
        print(f"FAILED to Create View. Error: {e}")


def update_view(production_conn, view_name, config_xml):
    """
    A function to update a specified view in Jenkins production environment.

    Args:
        production_conn: Connection to the Jenkins production environment.
        view_name: Name of the view to be updated.
        config_xml: Configuration XML for the updated view.

    Returns:
        None
    """
    try:
        production_conn.reconfig_view(view_name, config_xml)
        print(f"UPDATED on Jenkins-Production VIEW - {production_url}\t\t->\t{view_name}")
    except jenkins.JenkinsException as e:
        print(f"FAILED to Update View. Error: {e}")


def get_plugin_list(conn):
    """
    Get a list of plugins using the provided connection object.

    Args:
        conn: The connection object used to retrieve plugin information.

    Returns:
        list: A list of short names of the plugins.
    """
    try:
        plist = []
        for plugin in conn.get_plugins_info():
            plist.append(plugin.get('shortName'))
        return plist
    except Exception as e:
        print("Error in get_plugin_list: ", e)


def install_plugin_in_production(production_conn, to_install_plugins_list):
    """
    Installs a list of plugins in the production environment.

    Args:
        production_conn (object): The connection object for the production environment.
        to_install_plugins_list (list): A list of plugins to be installed.

    Returns:
        bool: True if all plugins are successfully installed, False otherwise.
    """
    try:
        flag_installed = []
        for plugin in to_install_plugins_list:
            try:
                print(f'INSTALLING: {plugin}')
                flag_installed.append(production_conn.install_plugin(plugin))
            except Exception as e:
                print(f"FAILED to Install Plugin. Error: {e}")
        if False in flag_installed:
            return False
        else:
            return True
    except Exception as e:
        print("Error in install_plugin_in_production: ", e)


def plugin_differences(production_conn, interim_conn):
    """
    Calculate the differences in plugins between two database connections.

    :param production_conn: The production database connection.
    :param interim_conn: The interim database connection.
    :return: A list of plugins that are in the interim database but not in the production database.
    """
    return list(set(get_plugin_list(interim_conn)).difference(get_plugin_list(production_conn)))


def check_job_plugins_in_production(production_conn, plugins_to_install_production, job, config_xml):
    """
    A function to check and install job-specific plugins in a production environment.

    Args:
        production_conn: The connection to the production environment.
        plugins_to_install_production: List of plugins to be installed in production.
        job: The job for which plugins are being checked and installed.
        config_xml: The configuration XML file for the job.

    Returns:
        bool: True if all plugins were successfully installed, False otherwise.
    """
    try:
        print(f'\nPLUGIN CHECK FOR {job}\n')
        job_specific_plugins = get_job_specific_plugins(
            config_xml)  # returns a list of jobs required for a particular job in interim
        plugins_to_install = list(set(plugins_to_install_production) & set(job_specific_plugins))
        print(f'Plugins to be INSTALLED for {job}: {plugins_to_install}')
        chk_flag = install_plugin_in_production(production_conn, plugins_to_install)
        if chk_flag:
            print(f'All Plugins INSTALLED in Production Server {production_url}\n\n')
            return True
        else:
            print(f'Install INITIATED, Please RESTART Production Server {production_url}\n\n')
            return False
    except Exception as e:
        print("Error in check_job_plugins_in_production: ", e)


def get_job_specific_plugins(config_xml):
    """
    Get job specific plugins from the given config XML.

    Parameters:
    - config_xml (str): The XML configuration to extract plugin information from.

    Returns:
    - list: A list of names of job-specific plugins extracted from the XML.
    """
    try:
        plugin_names = []
        try:
            tree = etree.fromstring(config_xml.encode())
        except etree.XMLSyntaxError as e:
            print(f"Error parsing XML: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return []

        plugin_elements = tree.xpath('//*[@plugin]')
        for plugin_attr in plugin_elements:
            plugin_name = plugin_attr.attrib['plugin'].split('@')[0]  # Get Name w/o Version
            plugin_names.append(plugin_name)

        return plugin_names
    except Exception as e:
        print("Error in get_job_specific_plugins: ", e)


def get_job_list(conn):
    """
    A function to retrieve a list of job names from the given connection object.

    Parameters:
    conn (connection object): The connection object used to retrieve job information.

    Returns:
    list: A list of job names extracted from the connection object.
    """
    try:
        job_list = []
        for job in conn.get_jobs():
            job_list.append(job['name'])
        return job_list
    except Exception as e:
        print("Error in get_job_list: ", e)


def get_views_list(conn):
    """
    Retrieves a list of views from the given connection.

    Args:
        conn: The connection object used to retrieve the views.

    Returns:
        list: A list of names of the views retrieved from the connection.
    """
    try:
        view_list = []
        for view in conn.get_views():
            view_list.append(view['name'])
        return view_list
    except Exception as e:
        print("Error in get_views_list: ", e)


def get_view_and_its_jobs(conn):
    """
    Generate a dictionary of views and their associated jobs.

    :param conn: The connection object to interact with the system.
    :return: A dictionary containing view names as keys and a list of job names as values.
    """
    try:
        view_list = {}
        for view in conn.get_views():
            if view['name'] != 'all':
                config_xml_views = get_view_config_xml(conn, view['name'])
                root = etree.fromstring(config_xml_views.encode('utf-8'))  # Parse the XML string with lxml
                view_list[view["name"]] = root.xpath('//jobNames/string/text()')
        return view_list
    except Exception as e:
        print("Error in get_view_and_its_jobs: ", e)


def get_view_config_xml(conn, view_name):
    """
    Retrieve the configuration XML for a specific view.

    Args:
        conn: The connection to the Jenkins server.
        view_name: The name of the view for which the configuration XML is to be retrieved.

    Returns:
        The configuration XML for the specified view, or None if an exception occurs.
    """
    try:
        config_xml = conn.get_view_config(view_name)
    except jenkins.JenkinsException:
        config_xml = None
    return config_xml


def check_views(production_conn, interim_conn, job_to_update, view_to_update='throughall'):
    """
    A function to check and update views in production based on jobs and views in interim connection.

    Parameters:
    - production_conn: Connection to the production environment.
    - interim_conn: Connection to the interim environment.
    - job_to_update: Job to be updated.
    - view_to_update: The view to be updated (default is 'throughall').

    Returns:
    None
    """
    try:
        # Get Views
        interim_specific_views_and_jobs = get_view_and_its_jobs(interim_conn)
        # print('Interim Jobs and Views', interim_specific_views_and_jobs)
        production_specific_views_and_jobs = get_view_and_its_jobs(production_conn)
        # print('Production Jobs and Views', production_specific_views_and_jobs)

        for view, jobs in interim_specific_views_and_jobs.items():

            # the below if condition is to narrow down the update/create operations

            if job_to_update in jobs and view_to_update == 'throughall' or job_to_update in \
                    production_specific_views_and_jobs.get(view, '') and view_to_update == 'throughall':
                if view in production_specific_views_and_jobs.keys():  # update view if present!
                    if job_to_update in jobs or production_specific_views_and_jobs[view]:
                        # now check if the view exists, else create one!
                        config_xml = get_view_config_xml(interim_conn, view)
                        if config_xml:
                            update_view(production_conn, view, config_xml)
                else:
                    if job_to_update in jobs:  # create view if not present!
                        config_xml = get_view_config_xml(interim_conn, view)
                        if config_xml:
                            create_view(production_conn, view, config_xml)

            elif job_to_update in jobs and view_to_update == view or job_to_update in production_specific_views_and_jobs.get(
                    view, '') and view_to_update == view:
                if view in production_specific_views_and_jobs.keys():
                    if job_to_update in jobs or production_specific_views_and_jobs[view]:
                        # now check if the view exists, else create one!
                        config_xml = get_view_config_xml(interim_conn, view)
                        if config_xml:
                            update_view(production_conn, view, config_xml)
                else:
                    if job_to_update in jobs:
                        config_xml = get_view_config_xml(interim_conn, view)
                        if config_xml:
                            create_view(production_conn, view, config_xml)

    except Exception as e:
        print("Error in check_views: ", e)


def production_view_clean_up(production_conn):
    """
    Function to clean up production views by deleting those with no associated jobs.

    Args:
        production_conn: The connection to the production environment.

    Returns:
        None
    """
    try:
        production_specific_views_and_jobs = get_view_and_its_jobs(production_conn)
        for view, jobs in production_specific_views_and_jobs.items():
            if len(jobs) == 0:
                production_conn.delete_view(view)
        print(f'\n\n\nProduction Server {production_url} Cleaned Up\n\n\n')

    except Exception as e:
        print("Production View Clean Up Failed. Error: ", e)


def chk_publish_job_standards(job_to_update):
    """
    Check if a job meets certain standards by comparing it with views and jobs from different connections.

    Parameters:
    job_to_update (str): The job to be checked against the views and jobs.

    Returns:
    bool: True if the job meets the standards, False otherwise.
    """
    try:
        view_list = []
        interim_specific_views_and_jobs = get_view_and_its_jobs(interim_conn)
        production_specific_views_and_jobs = get_view_and_its_jobs(production_conn)

        for view, jobs in interim_specific_views_and_jobs.items():
            if job_to_update in jobs or job_to_update in production_specific_views_and_jobs.get(view, ''):
                view_list.append(view)

        if len(view_list) == 1:
            return True

        elif len(view_list) == 0:
            print(f"\n\nNOT PRESENT IN ANY VIEW: Job\t\t->\t{job_to_update}\n\n")
            return False

        else:
            print(f"\n\nDUPLICATES of {job_to_update} Exists on Views\t\t->\t{view_list}\n\n")
            return False

    except Exception as e:
        print("Error in chk_publish_job_standards: ", e)


def view_pre_check(views_name_list):
    """
    A function that performs pre-checks on a list of views by checking their associated jobs against publish job standards.

    Parameters:
    - views_name_list: a list of view names to be checked

    Returns:
    - True if all jobs associated with the views pass the standards, False otherwise
    """
    try:
        interim_specific_views_and_jobs = get_view_and_its_jobs(interim_conn)
        for view in views_name_list:
            for job in interim_specific_views_and_jobs[view]:
                if not chk_publish_job_standards(job):
                    return False
        return True
    except Exception as e:
        print("Error in view_pre_check: ", e)


def job_pre_check(jobs_name_list):
    """
    A function that performs pre-checks on a list of job names to ensure they meet publishing standards.

    Parameters:
    jobs_name_list (list): A list of job names to be checked.

    Returns:
    bool: True if all jobs meet publishing standards, False otherwise.
    """
    try:
        for job in jobs_name_list:
            if not chk_publish_job_standards(job):
                return False
        return True

    except Exception as e:
        print("Error in job_pre_check: ", e)


def pre_check(action, list_name):
    """
    A function to perform pre-checks based on the action provided and the list of items and create check.json

    Parameters:
    - action (str): The type of action to be performed.
    - list_name (list): The list of items to be checked.

    Returns:
    - None
    """
    try:
        data = {"result": False, "job_list": None}
        if action == 'Jobs':

            temp = []
            job_name_list = list_name
            # Performing Pre-Check here, ensuring that there are no duplicate jobs present and plugins exist!
            if job_pre_check(job_name_list):
                for job in job_name_list:
                    config_xml = get_config_xml(interim_conn, job)
                    if config_xml:
                        job_specific_plugins_exist = check_job_plugins_in_production(production_conn,
                                                                                     plugins_to_install_production, job,
                                                                                     config_xml)
                        if job_specific_plugins_exist:
                            temp.append(True)
                        else:
                            temp.append(False)
                            print(f'Job Specific Plugin NOT INSTALLED in Production Server: {production_url}')
                    else:
                        temp.append(False)
                        print(f"{job}'s config.xml NOT RETRIEVED in Interim Server: {interim_url}")
                    print('_' * 101 + '\n\n')

                if False in temp:
                    result = False
                else:
                    result = True

            else:
                result = False

            data = {"result": result, "job_list": ", ".join(job_name_list)}

        elif action == "Views":

            view_name_list = list_name
            temp = []
            job_list = []
            if view_pre_check(view_name_list):
                for view in view_name_list:
                    for job in get_view_and_its_jobs(interim_conn)[view]:
                        job_list.append(job)
                        config_xml = get_config_xml(interim_conn, job)
                        if config_xml:
                            job_specific_plugins_exist = check_job_plugins_in_production(production_conn,
                                                                                         plugins_to_install_production, job,
                                                                                         config_xml)
                            if job_specific_plugins_exist:
                                temp.append(True)
                            else:
                                temp.append(False)
                                print(f'Job Specific Plugin {job} NOT INSTALLED in Production Server: {production_url}')
                        else:
                            temp.append(False)
                            print(f"{job}'s config.xml NOT RETRIEVED in Interim Server: {interim_url}")
                        print('_' * 101 + '\n\n')

                if False in temp:
                    result = False
                else:
                    result = True

            else:
                result = False

            data = {"result": result, "job_list": ", ".join(job_list)}

        with open("check.json", "w") as f:
            json.dump(data, f, indent=4)

    except Exception as e:
        print(f"Error pre_check: {e}")


def parse_arguments():
    """
    A function to parse the arguments provided to the script.
    """
    try:
        parser = argparse.ArgumentParser(description="Add '--check true' to ensure that check.properties is created")
        parser.add_argument("--function", help="True to check the jobs and views", type=str, required=True)

        return parser.parse_args()
    except Exception as e:
        print(f"Error parse_arguments: {e}")


if __name__ == "__main__":

    # Get these values from the Environment

    try:

        action = os.environ['Publish']
        list_name = os.environ['Publish_List']
        args = parse_arguments()
        function = args.function

        # Credentials used for Jenkins Server Connection
        production_url = ""
        interim_url = ""
        production_username = ""
        interim_username = ""
        production_password = ""
        interim_password = ""

        list_name = list_name.split(',')
        list_name = [job.strip() for job in list_name if job]

        if production_url == '' or interim_url == '' or len(list_name) == 0:
            print('\n\n\nError: Fill the Required Fields!\n\n')
            exit(1)

        production_conn, interim_conn = establish_connection_to_servers(production_url, interim_url, production_username,
                                                                        interim_username, production_password, interim_password)

        plugins_to_install_production = plugin_differences(production_conn, interim_conn)

        interim_jobs_list = get_job_list(interim_conn)
        production_jobs_list = get_job_list(production_conn)
        interim_views_list = get_views_list(interim_conn)
        production_views_list = get_views_list(production_conn)

        if function.lower() == 'check' and function is not None:
            pre_check(action, list_name)
            print("\n\n\ncheck.json file GENERATED!\n\n")

        elif function.lower() == 'publish' and function is not None:

            if action == 'Jobs':

                job_name_list = list_name

                # Performing Pre-Check here, ensuring that there are no duplicate jobs present!
                if not job_pre_check(job_name_list):
                    exit(1)

                print('\n\nJOB MOVEMENT DETAILS\n')
                # Update Specific Jobs
                if len(job_name_list) != 0:
                    for job in job_name_list:
                        print('\n' + job, end='\n' + '_' * 101 + '\n\n')
                        if job in interim_jobs_list:
                            config_xml = get_config_xml(interim_conn, job)
                            if config_xml:

                                job_specific_plugins_exist = check_job_plugins_in_production(production_conn,
                                                                                             plugins_to_install_production, job,
                                                                                             config_xml)  # this should basically be 1 function, that returns a boolean value True if all the plugins are present, else

                                if job_specific_plugins_exist:

                                    print('PUBLISHING DETAILS\n')
                                    if job in production_jobs_list:
                                        update_job(production_conn, job, config_xml)
                                    else:
                                        create_job(production_conn, job, config_xml)
                                    check_views(production_conn, interim_conn, job)

                                else:
                                    print(f"Job Specific Plugin NOT INSTALLED in Production Server: {production_url}")
                            else:
                                print(f"{job}'s config.xml NOT RETRIEVED in Interim Server: {interim_url}")
                        else:
                            print(f"{job} DOES NOT Exist in Interim Server: {interim_url}")
                        print('_' * 101 + '\n\n')

                else:
                    print('Enter Job Details to Move/Update')

            elif action == 'Views':

                views_name_list = list_name
                job = ''
                flag_update = False
                # print(views_name_list)

                # Performing Pre-Check here, ensuring that there are no duplicate jobs present!
                if not view_pre_check(views_name_list):
                    exit(1)

                print('\n\nVIEW MOVEMENT DETAILS\n')
                # Update Specific Views, and all jobs within
                if len(views_name_list) != 0:
                    for view in views_name_list:
                        print('\n' + view, end='\n' + '_' * 101 + '\n\n')
                        if view in interim_views_list:
                            interim_jobs_list = get_view_and_its_jobs(interim_conn)[view]
                            for job in interim_jobs_list:
                                print('\n' + job, end='\n' + '_' * 101 + '\n\n')
                                # check the required plugins are installed in the Production, if not, skip
                                config_xml = get_config_xml(interim_conn, job)
                                if config_xml:

                                    job_specific_plugins_exist = check_job_plugins_in_production(production_conn,
                                                                                                 plugins_to_install_production,
                                                                                                 job,
                                                                                                 config_xml)  # this should basically be 1 function, that returns a boolean value True if all the plugins are present, else
                                    if job_specific_plugins_exist:

                                        print('PUBLISHING DETAILS\n')
                                        if job in production_jobs_list:
                                            flag_update = True
                                            update_job(production_conn, job, config_xml)
                                        else:
                                            flag_update = True
                                            create_job(production_conn, job, config_xml)

                                    else:
                                        print(f'Job Specific Plugin NOT INSTALLED in Production Server: {production_url}')
                                else:
                                    print(f"{job}'s config.xml NOT RETRIEVED in Interim Server: {interim_url}")
                                print('_' * 101 + '\n\n')
                        # Updating the View once the jobs have been updated/created
                        if flag_update:
                            check_views(production_conn, interim_conn, job, view)
                        flag_update = False
                else:
                    print('Enter View Details to Move/Update')

            production_view_clean_up(production_conn)

    except Exception as e:
        print("Exception in Main Function: ", e)
